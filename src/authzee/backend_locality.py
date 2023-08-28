
from enum import Enum

class BackendLocality(Enum):
    """Describes the the scope or "locality" of where compute or storage backends exist.

    - ``MAIN_PROCESS`` 
        - Compute runs in same process as the ``authzee`` app.
        - Storage is limited to the same process as the ``authzee`` app.
    - ``NETWORK`` 
        - Compute resources are communicated to over the network.  They are external to the system running the ``authzee`` app.
        - Storage is reachable over the network. It is (or can be) external to the system running the ``authzee`` app.
    - ``SYSTEM`` 
        - Compute resources are on the same system as the ``authzee`` app.
        - Storage is limited to the system running the ``authzee`` app.


    Likely compatibility:

    - ``MAIN_PROCESS``compute may be compatible with all storage localities.
    - ``NETWORK`` compute may only be compatible with ``NETWORK`` storage. 
    - ``SYSTEM`` compute may only be compatible with ``SYSTEM`` and ``NETWORK`` storage.

    """

    MAIN_PROCESS: str = "MAIN_PROCESS"
    NETWORK: str = "NETWORK"
    SYSTEM: str = "SYSTEM"

