import sqlite3

conn = sqlite3.connect('plema.db')
c = conn.cursor()
c.execute("DELETE FROM settings WHERE key='account_username'")
c.execute("DELETE FROM settings WHERE key='account_password'")
conn.commit()
conn.close()
print('✓ Account credentials deleted successfully! You can now sign up again when you reopen the app.')
