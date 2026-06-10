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


async def test_list_classes_returns_all(client: AsyncClient) -> None:
    t1 = await _register(client, "t1@example.com")
    t2 = await _register(client, "t2@example.com")
    await _create_class(client, t1["headers"], name="A")
    await _create_class(client, t1["headers"], name="B")
    await _create_class(client, t2["headers"], name="C")

    resp = await client.get(CLASSES, headers=t1["headers"])

    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 3


async def test_list_classes_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(CLASSES)

    assert resp.status_code == 401


async def test_list_classes_pagination(client: AsyncClient) -> None:
    teacher = await _register(client, "teacher@example.com")
    for name in ("A", "B", "C"):
        await _create_class(client, teacher["headers"], name=name)

    first = await client.get(
        CLASSES, params={"page": 1, "size": 2}, headers=teacher["headers"]
    )
    body = first.json()
    assert len(body["data"]) == 2
    assert body["pagination"] == {"page": 1, "size": 2, "total": 3}

    second = await client.get(
        CLASSES, params={"page": 2, "size": 2}, headers=teacher["headers"]
    )
    body2 = second.json()
    assert len(body2["data"]) == 1
    assert body2["pagination"]["total"] == 3
    # No overlap between pages.
    assert {c["id"] for c in body["data"]}.isdisjoint(c["id"] for c in body2["data"])


async def test_list_classes_invalid_pagination_returns_422(
    client: AsyncClient,
) -> None:
    user = await _register(client, "user@example.com")

    resp = await client.get(CLASSES, params={"size": 0}, headers=user["headers"])

    assert resp.status_code == 422


async def test_list_classes_relation_owner(client: AsyncClient) -> None:
    t1 = await _register(client, "t1@example.com")
    t2 = await _register(client, "t2@example.com")
    await _create_class(client, t1["headers"], name="A")
    await _create_class(client, t1["headers"], name="B")
    await _create_class(client, t2["headers"], name="C")

    # t1 sees only the classes they teach.
    resp = await client.get(
        CLASSES, params={"relation": "owner"}, headers=t1["headers"]
    )

    data = resp.json()["data"]
    assert len(data) == 2
    assert all(c["teacher_id"] == t1["id"] for c in data)


async def test_list_classes_relation_joiner(client: AsyncClient, redis_client) -> None:
    teacher = await _register(client, "teacher@example.com")
    student = await _register(client, "student@example.com")
    joined = await _create_class(client, teacher["headers"], name="Joined")
    await _create_class(client, teacher["headers"], name="Other")
    await client.post(f"{CLASSES}/{joined['id']}/enroll", headers=student["headers"])

    # The student sees only the class they joined.
    resp = await client.get(
        CLASSES, params={"relation": "joiner"}, headers=student["headers"]
    )

    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == joined["id"]
    assert data[0]["enrolled_count"] == 1


async def test_list_classes_invalid_relation_returns_422(client: AsyncClient) -> None:
    user = await _register(client, "user@example.com")

    resp = await client.get(
        CLASSES, params={"relation": "nope"}, headers=user["headers"]
    )

    assert resp.status_code == 422


async def test_list_students_in_class(client: AsyncClient, redis_client) -> None:
    teacher = await _register(client, "teacher@example.com")
    s1 = await _register(client, "s1@example.com")
    s2 = await _register(client, "s2@example.com")
    classroom = await _create_class(client, teacher["headers"])
    await client.post(f"{CLASSES}/{classroom['id']}/enroll", headers=s1["headers"])
    await client.post(f"{CLASSES}/{classroom['id']}/enroll", headers=s2["headers"])

    resp = await client.get(
        f"{CLASSES}/{classroom['id']}/students", headers=teacher["headers"]
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert sorted(s["email"] for s in data) == ["s1@example.com", "s2@example.com"]
    assert all(s["enrolled_at"] for s in data)


async def test_list_students_missing_class_returns_404(client: AsyncClient) -> None:
    user = await _register(client, "user@example.com")

    resp = await client.get(f"{CLASSES}/999/students", headers=user["headers"])

    assert resp.status_code == 404
