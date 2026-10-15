"""Import workflows under their canonical package name for Temporal replay."""
import asyncio
from tenderproof.workflows import main

if __name__ == '__main__':
    asyncio.run(main())
