import pytest
from unittest.mock import AsyncMock, Mock

from api.v1.exceptions import BadRequestError
from api.v1.routes.files import upload
from models.molecule_info import MoleculeSetStats

HASH_A = "a" * 64
HASH_B = "b" * 64


def make_stats(molecules: int, counts: dict[str, int]) -> MoleculeSetStats:
    return MoleculeSetStats(
        {
            "total_molecules": molecules,
            "total_atoms": sum(counts.values()),
            "atom_type_counts": [{"symbol": s, "count": c} for s, c in counts.items()],
        }
    )


STATS = {
    HASH_A: make_stats(2, {"C": 12, "H": 13, "O": 2}),
    HASH_B: make_stats(1, {"C": 5, "N": 1}),
}


def upload_file(name: str, file_hash: str) -> Mock:
    file = Mock()
    file.filename = name
    file.size = 100
    file.file_hash = file_hash
    return file


@pytest.fixture
def request_mock():
    request = Mock()
    request.state.user = None
    return request


@pytest.fixture
def io_mock():
    io = Mock()
    io.get_file_storage_path.return_value = "/data/guest/files"
    io.store_upload_file = AsyncMock(
        side_effect=lambda file, workdir: (
            f"{workdir}/{file.file_hash}_{file.filename}",
            file.file_hash,
        )
    )
    io.parse_filename.side_effect = lambda filename: (filename[:64], filename[65:])
    return io


@pytest.fixture
def storage_mock():
    return Mock()


@pytest.fixture
def chargefw2_mock():
    chargefw2 = Mock()
    chargefw2.info = AsyncMock(side_effect=lambda path: STATS[path.split("/")[-1][:64]])
    return chargefw2


async def call_upload(request, files, io, storage, chargefw2):
    response = await upload(request, files, io=io, storage_service=storage, chargefw2=chargefw2)
    # Serialize the way FastAPI does, i.e. with camelCase aliases.
    return response.model_dump(by_alias=True, mode="json")


@pytest.mark.asyncio
async def test_upload_returns_stats_for_each_file(
    request_mock, io_mock, storage_mock, chargefw2_mock
):
    files = [upload_file("molecules.sdf", HASH_A), upload_file("protein.pdb", HASH_B)]

    body = await call_upload(request_mock, files, io_mock, storage_mock, chargefw2_mock)

    assert body["success"] is True
    assert body["data"] == [
        {
            "file": "molecules.sdf",
            "fileHash": HASH_A,
            "stats": {
                "totalMolecules": 2,
                "totalAtoms": 27,
                "atomTypeCounts": [
                    {"symbol": "C", "count": 12},
                    {"symbol": "H", "count": 13},
                    {"symbol": "O", "count": 2},
                ],
            },
        },
        {
            "file": "protein.pdb",
            "fileHash": HASH_B,
            "stats": {
                "totalMolecules": 1,
                "totalAtoms": 6,
                "atomTypeCounts": [
                    {"symbol": "C", "count": 5},
                    {"symbol": "N", "count": 1},
                ],
            },
        },
    ]


@pytest.mark.asyncio
async def test_upload_returns_the_stats_it_stores(
    request_mock, io_mock, storage_mock, chargefw2_mock
):
    files = [upload_file("molecules.sdf", HASH_A)]

    await call_upload(request_mock, files, io_mock, storage_mock, chargefw2_mock)

    chargefw2_mock.info.assert_awaited_once_with(f"/data/guest/files/{HASH_A}_molecules.sdf")
    storage_mock.store_file_info.assert_called_once_with(HASH_A, STATS[HASH_A])


@pytest.mark.asyncio
async def test_upload_of_duplicate_content_returns_separate_entries(
    request_mock, io_mock, storage_mock, chargefw2_mock
):
    files = [upload_file("first.sdf", HASH_A), upload_file("second.sdf", HASH_A)]

    body = await call_upload(request_mock, files, io_mock, storage_mock, chargefw2_mock)

    assert [entry["file"] for entry in body["data"]] == ["first.sdf", "second.sdf"]
    assert [entry["fileHash"] for entry in body["data"]] == [HASH_A, HASH_A]
    assert all(entry["stats"]["totalAtoms"] == 27 for entry in body["data"])


@pytest.mark.asyncio
async def test_upload_of_unreadable_file_fails_and_removes_stored_files(
    request_mock, io_mock, storage_mock, chargefw2_mock
):
    chargefw2_mock.info = AsyncMock(
        side_effect=RuntimeError("No molecules were loaded from the input file")
    )
    files = [upload_file("broken.sdf", HASH_A)]

    with pytest.raises(BadRequestError) as error:
        await call_upload(request_mock, files, io_mock, storage_mock, chargefw2_mock)

    assert error.value.detail == "No molecules were loaded from the input file"
    io_mock.remove_file.assert_called_once_with(f"/data/guest/files/{HASH_A}_broken.sdf")
    storage_mock.store_file_info.assert_not_called()
