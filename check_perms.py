
import os
import stat

path = "/etc/pp2host/static/ban.dat"

print(f"Checking permissions for: {path}")

if not os.path.exists(path):
    print("❌ File does not exist")
else:
    print("✅ File exists")
    
    # Check stats
    st = os.stat(path)
    print(f"  Owner UID: {st.st_uid}")
    print(f"  Group GID: {st.st_gid}")
    print(f"  Permissions: {oct(st.st_mode)}")
    
    # Check access
    can_read = os.access(path, os.R_OK)
    can_write = os.access(path, os.W_OK)
    
    print(f"  Read access: {'✅ YES' if can_read else '❌ NO'}")
    print(f"  Write access: {'✅ YES' if can_write else '❌ NO'}")
    
    if not can_write:
        print("\n⚠️  User does not have write access. This is likely the cause of the unban failure.")
        import getpass
        print(f"   Current user: {getpass.getuser()}")

