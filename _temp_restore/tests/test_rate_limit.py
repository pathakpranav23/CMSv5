def test_login_rate_limit(client):
    for i in range(5):
        res = client.post("/login", data={"username": "wrong", "password": "wrong"})
        assert res.status_code in (200, 401, 403)
    res = client.post("/login", data={"username": "wrong", "password": "wrong"})
    assert res.status_code == 429


def test_forgot_password_rate_limit(client):
    for i in range(3):
        res = client.post("/forgot-password", data={"username": "nouser@example.com"})
        assert res.status_code in (200, 302)
    res = client.post("/forgot-password", data={"username": "nouser@example.com"})
    assert res.status_code == 429