import sys
from app import app, db, User

def promote_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Error: User '{username}' not found.")
            return

        user.role = 'super_admin'
        try:
            db.session.commit()
            print(f"✅ Success: User '{username}' has been promoted to SUPER ADMIN.")
            print("🚀 They now have full authority to delete other users.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: Could not update database. {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <username>")
    else:
        promote_user(sys.argv[1])
