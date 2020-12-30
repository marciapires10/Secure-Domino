import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


r1 = os.urandom(128)
r2 = os.urandom(128)
digest = hashes.Hash(hashes.SHA256(), default_backend())
digest.update(b"6:6 6:5 6:4 6:3")
digest2 = digest.copy()
digest.update(r1)
digest.update(r2)
bitcommit = digest.finalize()
print(bitcommit)
digest2.update(r1)
digest2.update(r2)
bitcommit2 = digest2.finalize()
if(bitcommit == bitcommit2):
    print("true")
