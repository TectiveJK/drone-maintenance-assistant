from app.database import connect, now


def create_issue(drone_id, source, description):
    con = connect()
    con.execute(
        "INSERT INTO maintenance_issues(drone_id,source,description,status,created_at) VALUES(?,?,?,?,?)",
        (drone_id, source, description, "OPEN", now()),
    )
    con.commit(); con.close()


def close_issue(issue_id):
    con = connect(); con.execute("UPDATE maintenance_issues SET status='CLOSED' WHERE id=?", (issue_id,)); con.commit(); con.close()
