
from enum import Enum


class BackendLocality(Enum):
    """Describes the the scope or "locality" of where compute or storage backends exist and communicate.

    - ``PROCESS`` 
        - Compute runs in same process as the ``authzee`` app.
        - Storage is limited to the same process as the ``authzee`` app.
    - ``SYSTEM`` 
        - Compute resources are on the same system as the ``authzee`` app.
        - Storage is limited to the system running the ``authzee`` app.
    - ``NETWORK`` 
        - Compute resources are communicated to over the network.  They are external to the system running the ``authzee`` app.
        - Storage is reachable over the network. It is (or can be) external to the system running the ``authzee`` app.
    
    The purpose of this enum is to help people identify incompatibilities in compute and storage backends for authzee. 
    See the ``authzee.compute_compatibility`` dictionary for the compatibility matrix. 
    Keys are the compute localities, and the values are sets of compatible storage localities.
    """
    PROCESS: str = "PROCESS"
    SYSTEM: str = "SYSTEM"
    NETWORK: str = "NETWORK"
    

compute_compatibility = {
    BackendLocality.PROCESS: {
        BackendLocality.PROCESS,
        BackendLocality.SYSTEM,
        BackendLocality.NETWORK
    },
    BackendLocality.SYSTEM: {
        BackendLocality.SYSTEM,
        BackendLocality.NETWORK
    },
    BackendLocality.NETWORK: {
        BackendLocality.NETWORK
    }
}