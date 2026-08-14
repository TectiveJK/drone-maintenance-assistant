from app.database import connect, now


def init_battery_table():
    con = connect()
    con.execute('''CREATE TABLE IF NOT EXISTS batteries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drone_id INTEGER,
        battery_id TEXT NOT NULL,
        cycles INTEGER DEFAULT 0,
        voltage TEXT,
        health TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(drone_id) REFERENCES drones(id)
    )''')
    con.commit(); con.close()


def add_battery(drone_id, battery_id, cycles=0, voltage="", health="", notes=""):
    init_battery_table(); con = connect()
    con.execute("INSERT INTO batteries(drone_id,battery_id,cycles,voltage,health,notes,created_at) VALUES(?,?,?,?,?,?,?)", (drone_id,battery_id,cycles,voltage,health,notes,now()))
    con.commit(); con.close()
