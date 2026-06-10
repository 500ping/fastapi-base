from httpx import AsyncClient

SIGNUP = "/api/v1/auth/signup"
SIGNIN = "/api/v1/auth/signin"
CLASSES = "/api/v1/courses/classes"


async def _register(client: AsyncClient, email: str) -> dict:
    """Sign a user up and in; return {"id", "headers"}."""
    password = "supersecret"
    signup = await client.post(SIGNUP, json={"email": email, "password": password})
    user_id = signup.json()["data"]["id"]
    signin = await client.post(SIGNIN, json={"email": email, "password": password})
    token = signin.json()["data"]["access_token"]
    return {"id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


async def _create_class(client: AsyncClient, headers: dict, **over) -> dict:
    payload = {"name": "Algorithms 101", **over}
    resp = await client.post(CLASSES, json=payload, headers=headers)
    return resp.json()["data"]


async def test_create_class_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(CLASSES, json={"name": "Algorithms 101"})

    assert resp.status_code == 401


async def test_create_class_owner_is_current_user(client: AsyncClient) -> None:
    teacher = await _register(client, "teacher@example.com")

    resp = await client.post(
        CLASSES, json={"name": "Algorithms 101"}, headers=teacher["headers"]
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["teacher_id"] == teacher["id"]
    assert data["capacity"] == 40
    assert data["enrolled_count"] == 0


async def test_one_teacher_can_manage_multiple_classes(client: AsyncClient) -> None:
    teacher = await _register(client, "teacher@example.com")

    first = await _create_class(client, teacher["headers"], name="Algorithms")
    second = await _create_class(client, teacher["headers"], name="Data Structures")

    assert first["teacher_id"] == second["teacher_id"] == teacher["id"]
    assert first["id"] != second["id"]


async def test_student_self_enrolls(client: AsyncClient, redis_client) -> None:
    teacher = await _register(client, "teacher@example.com")
    student = await _register(client, "student@example.com")
    classroom = await _create_class(client, teacher["headers"])

    resp = await client.post(
        f"{CLASSES}/{classroom['id']}/enroll", headers=student["headers"]
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["class_id"] == classroom["id"]
    assert data["student_id"] == student["id"]

    detail = await client.get(
        f"{CLASSES}/{classroom['id']}", headers=teacher["headers"]
    )
    assert detail.json()["data"]["enrolled_count"] == 1


async def test_one_student_can_join_multiple_classes(
    client: AsyncClient, redis_client
) -> None:
    teacher = await _register(client, "teacher@example.com")
    student = await _register(client, "student@example.com")
    first = await _create_class(client, teacher["headers"], name="Algorithms")
    second = await _create_class(client, teacher["headers"], name="Data Structures")

    r1 = await client.post(
        f"{CLASSES}/{first['id']}/enroll", headers=student["headers"]
    )
    r2 = await client.post(
        f"{CLASSES}/{second['id']}/enroll", headers=student["headers"]
    )

    assert r1.status_code == 201
    assert r2.status_code == 201


async def test_duplicate_enrollment_returns_409(
    client: AsyncClient, redis_client
) -> None:
    teacher = await _register(client, "teacher@example.com")
    student = await _register(client, "student@example.com")
    classroom = await _create_class(client, teacher["headers"])
    url = f"{CLASSES}/{classroom['id']}/enroll"

    await client.post(url, headers=student["headers"])
    resp = await client.post(url, headers=student["headers"])

    assert resp.status_code == 409
    assert resp.json()["msg"] == "Already enrolled in this class"


async def test_enroll_into_missing_class_returns_404(
    client: AsyncClient, redis_client
) -> None:
    student = await _register(client, "student@example.com")

    resp = await client.post(f"{CLASSES}/999/enroll", headers=student["headers"])

    assert resp.status_code == 404
    assert resp.json()["msg"] == "Class not found"


async def test_enroll_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(f"{CLASSES}/1/enroll")

    assert resp.status_code == 401


async def test_get_missing_class_returns_404(client: AsyncClient) -> None:
    user = await _register(client, "user@example.com")

    resp = await client.get(f"{CLASSES}/999", headers=user["headers"])

    assert resp.status_code == 404
