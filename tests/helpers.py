def login(user, testapp):
    res = testapp.post(
        "/", params={"email": user.email, "password": user.test_password}
    ).follow()
    assert "Přihlášení proběhlo úspěšně" in res
