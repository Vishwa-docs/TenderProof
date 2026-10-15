"""Pure, deterministic checks. Solver results concern encoded claims only."""
from decimal import Decimal, InvalidOperation
import z3

UNITS = {'MVA':('apparent_power', '1000000'), 'kVA':('apparent_power','1000'),
         'VA':('apparent_power','1'), 'kV':('voltage','1000'), 'V':('voltage','1'),
         'kW':('active_power','1000'), 'W':('active_power','1'), '%':('percent','1')}


def quantity(value, unit):
    dimension, factor = UNITS[unit]
    result = Decimal(str(value)) * Decimal(factor)
    if not result.is_finite():
        raise ValueError('Non-finite quantity')
    return dimension, result


def constraint(variable, operator, value):
    number = z3.RealVal(str(value))
    if operator == 'eq': return variable == number
    if operator == 'ge': return variable >= number
    if operator == 'le': return variable <= number
    raise ValueError('Unsupported operator')


def assess_requirement(requirement, supplier):
    r, s = requirement, supplier
    result = dict(requirement_id=r['id'], supplier_id=s['id'], status='unknown',
                  reason='', counterexample=None, source_ids=list(r['source_ids']))
    def finish(status, reason, counterexample=None):
        result.update(status=status, reason=reason, counterexample=counterexample)
        return result
    if r.get('status') != 'approved':
        return finish('unknown', 'Engineering interpretation has not been approved.')
    if r.get('equipment_type', 'transformer') != 'transformer':
        return finish('unknown', 'Equipment type is outside the validated transformer rules.')
    candidates = [f for f in s['facts'] if f['property'] == r['property']
                  and f.get('conditions', {}) == r.get('conditions', {})]
    if not candidates:
        return finish('unknown', 'No guarantee covers the exact required operating conditions.')
    try:
        dim, required = quantity(r['value'], r['unit'])
        variable = z3.Real('guaranteed_value')
        solver = z3.Solver(); solver.set(timeout=2000)
        for fact in candidates:
            fdim, value = quantity(fact['value'], fact['unit'])
            if dim != fdim:
                return finish('unknown', 'The supplied and required units have different dimensions.')
            solver.add(constraint(variable, fact['operator'], value))
            result['source_ids'].extend(fact['source_ids'])
        # Check satisfiability first: contradictory guarantees must not prove anything.
        consistent = solver.check()
        if consistent == z3.unsat:
            return finish('conflicting', 'Supplier guarantees are mutually inconsistent under the same conditions.')
        if consistent == z3.unknown:
            return finish('unknown', 'The solver could not establish consistency.')
        solver.add(z3.Not(constraint(variable, r['operator'], required)))
        implication = solver.check()
        if implication == z3.unsat:
            return finish('supported', 'The encoded supplier guarantee covers the approved requirement.')
        if implication == z3.unknown:
            return finish('unknown', 'The solver could not resolve the implication.')
        raw = solver.model().eval(variable)
        factor = Decimal(UNITS[r['unit']][1])
        display = str(Decimal(raw.numerator_as_long()) / Decimal(raw.denominator_as_long()) / factor)
        return finish('contradicted', 'The supplier can satisfy its guarantee while the customer requirement fails.',
                      {'property':r['property'],'value':display,'unit':r['unit'],'conditions':r.get('conditions',{})})
    except (KeyError, ValueError, InvalidOperation, z3.Z3Exception):
        return finish('unknown', 'Unsupported or invalid quantity; engineering review is required.')


def assess_evidence(evidence, supplier, requirements):
    e, s = evidence, supplier
    result = dict(evidence_id=e['id'],supplier_id=s['id'],status='unknown',reason='',source_ids=e['source_ids'])
    def finish(status, reason):
        result.update(status=status,reason=reason); return result
    for field in ('configuration','revision'):
        if not s.get(field):return finish('unknown', f'Selected equipment {field} is unknown.')
        if not e.get(field): return finish('unknown', f'Missing equipment {field}.')
        if e[field] != s[field]: return finish('contradicted', f"Report {field} {e[field]} does not match selected {s[field]}.")
    if e['kind'] == 'routine':
        if not s.get('serial'):return finish('unknown','Selected equipment serial number is unknown.')
        if not e.get('serial'): return finish('unknown', 'Unit-specific report has no serial number.')
        if e['serial'] != s['serial']: return finish('contradicted', 'Routine report concerns a different serial number.')
    elif e['kind'] == 'type':
        if not e.get('family') or not s.get('family'):return finish('unknown','Explicit design-family identifiers are required.')
        if e.get('family') != s.get('family'): return finish('contradicted','Type report concerns a different design family.')
        if not e.get('approved_family_coverage'): return finish('unknown','Design-family coverage requires explicit authorized inspection approval.')
    else:
        return finish('unknown', 'Identity evidence alone does not establish acceptance performance.')
    if not requirements: return finish('unknown','No approved acceptance criteria are available.')
    refs={ref for measurement in e.get('measurements',[]) for ref in measurement.get('source_ids',[])}
    if not refs or not refs.issubset(set(e['source_ids'])):
        return finish('unknown','Measurements must cite this test evidence rather than a supplier guarantee.')
    measurements=[]
    report_conditions=e.get('conditions',{})
    for measurement in e.get('measurements',[]):
        local_conditions=measurement.get('conditions',{})
        if any(key in local_conditions and local_conditions[key]!=value for key,value in report_conditions.items()):
            return finish('conflicting','Report-level operating conditions conflict with a measurement; local conditions cannot override the report.')
        measurements.append({**measurement,'conditions':{**report_conditions,**local_conditions}})
    measured = {**s, 'facts': measurements}
    checks = [assess_requirement(r, measured) for r in requirements]
    statuses = {c['status'] for c in checks}
    if 'conflicting' in statuses: return finish('conflicting','Measurements under the same conditions conflict.')
    if 'contradicted' in statuses: return finish('contradicted','Applicable test measurements do not cover all customer requirements.')
    if 'unknown' in statuses: return finish('unknown','An acceptance criterion is unapproved, or a required measurement or operating condition is missing.')
    return finish('supported','Configuration, revision, evidence scope and encoded measurements are applicable.')


def compare_options(package):
    rows=[]
    currencies={s['currency'] for s in package['suppliers'] if s.get('currency')}
    price_bases={s.get('price_basis') for s in package['suppliers'] if s.get('price_cents') is not None}
    for s in package['suppliers']:
        checks=[assess_requirement(r,s) for r in package['requirements']]
        states={c['status'] for c in checks}
        status = 'rejected' if states & {'contradicted','conflicting'} else 'conditional' if 'unknown' in states or not checks else 'feasible'
        baseline=package['required_delivery_week']
        delivery_basis=s.get('delivery_basis')
        delay=max(0,s['delivery_weeks']-baseline) if baseline is not None and s.get('delivery_weeks') is not None and delivery_basis=='project_start' else None
        if delay and status == 'feasible': status='conditional'
        issues=[c['reason'] for c in checks if c['status']!='supported']
        if not s.get('configuration'):
            if status=='feasible':status='conditional'
            issues.append('Selected equipment configuration is unknown; a source-supported configuration is required before release.')
        if baseline is None:
            if status=='feasible':status='conditional'
            issues.append('A source-linked required delivery milestone must be approved.')
        missing=[field for field in ('price_cents','currency','delivery_weeks') if s.get(field) is None]
        if missing:
            if status=='feasible':status='conditional'
            issues.append('Commercial inputs are unknown: '+', '.join(missing)+'.')
        ancillary_unknown=[field.removesuffix('_cents') for field in ('expedite_cents','rework_cents') if s.get(field) is None]
        if ancillary_unknown:
            if status=='feasible':status='conditional'
            issues.append('Ancillary costs are unresolved: '+', '.join(ancillary_unknown)+'. The documented subtotal includes only known amounts; it is not a full-cost estimate.')
        if s.get('delivery_weeks') is not None and delivery_basis!='project_start':
            if status=='feasible':status='conditional'
            origin={'after_drawing_approval':'counted from approval of drawings, which has no approved date',
                    'after_order':'counted from the order, which has no approved date',
                    'other':'counted from another event, which has no approved date'}.get(delivery_basis,'counted from an event that the source does not state (basis not stated)')
            issues.append(f"Delivery of {s['delivery_weeks']} weeks is {origin}; it cannot be compared with a project-week milestone.")
        if s.get('price_cents') is not None and (s.get('price_basis') is None or len(price_bases)>1):
            if status=='feasible':status='conditional'
            issues.append('Offers state different or unstated price bases (unit price versus combined lot total); prices are not comparable like-for-like. Price basis for this offer: '+(s.get('price_basis') or 'not stated')+'.')
        if len(currencies)>1:
            if status=='feasible':status='conditional'
            issues.append('Offers use different currencies; no approved exchange-rate comparison is available.')
        if delay: issues.append(f'Delivery misses the required milestone by {delay} weeks; schedule review required.')
        # Retain a null offer subtotal when the base price is absent. Otherwise
        # sum only documented amounts; unknown ancillary costs still block gates.
        total=s['price_cents']+sum(s[field] for field in ('expedite_cents','rework_cents') if s.get(field) is not None) if s.get('price_cents') is not None else None
        rows.append(dict(supplier_id=s['id'],status=status,total_cents=total,
                         currency=s['currency'],delivery_weeks=s['delivery_weeks'],delivery_basis=delivery_basis,
                         price_basis=s.get('price_basis'),delay_weeks=delay,issues=issues))
    return sorted(rows,key=lambda x:({'feasible':0,'conditional':1,'rejected':2}[x['status']],x['total_cents'] if x['total_cents'] is not None else float('inf')))


def witness_for(requirement):
    if requirement['property']=='rated_power' and requirement.get('conditions',{}).get('cooling')=='ONAN':
        required=Decimal(requirement['value']); lower=required-Decimal(5)
        return dict(question=f'Would {lower} {requirement["unit"]} without fans and {required} {requirement["unit"]} with fans satisfy this requirement?',
                    configuration={'ONAN':str(lower),'ONAF':str(required)},expected=requirement['operator']=='le')
    return dict(question=None,configuration={},expected=None)
