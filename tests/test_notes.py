# tests/test_notes.py
def _login(client, email, pwd):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200
    return r.get_json()["access_token"]

def test_notes_crud_and_acl(client):
    # Créer 2 users
    for e in ("bob@example.com", "carol@example.com"):
        client.post("/api/v1/auth/register", json={"email": e, "password": "SuperSecret123"})

    # Promouvoir bob en admin (via SQL)
    from app.extensions import db
    from app.users.models import User
    with client.application.app_context():
        u = User.query.filter_by(email="bob@example.com").first()
        u.role = "admin"
        db.session.commit()

    access_admin = _login(client, "bob@example.com", "SuperSecret123")
    access_carol = _login(client, "carol@example.com", "SuperSecret123")

    # Carol crée une note
    r = client.post("/api/v1/notes/", headers={"Authorization": f"Bearer {access_carol}"},
                    json={"title":"N1","content":"C1"})
    assert r.status_code == 201
    note_id = r.get_json()["id"]

    # Carol voit sa note
    r = client.get(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_carol}"})
    assert r.status_code == 200

    # Admin voit la note de Carol
    r = client.get(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_admin}"})
    assert r.status_code == 200

    # Un autre user (faux) doit être 403 — on crée dave
    client.post("/api/v1/auth/register", json={"email": "dave@example.com", "password": "SuperSecret123"})
    access_dave = _login(client, "dave@example.com", "SuperSecret123")

    r = client.get(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_dave}"})
    assert r.status_code == 403

    # Carol met à jour sa note
    r = client.patch(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_carol}"},
                     json={"title":"N1-EDIT"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "N1-EDIT"

    # Carol supprime sa note
    r = client.delete(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_carol}"})
    assert r.status_code == 204

    # re-get -> 404
    r = client.get(f"/api/v1/notes/{note_id}", headers={"Authorization": f"Bearer {access_carol}"})
    assert r.status_code == 404
