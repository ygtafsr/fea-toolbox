import pytest

from featoolbox.IO.readerbase import Reader


def test_reader_requires_read_implementation() -> None:
    with pytest.raises(TypeError):
        Reader()


def test_reader_subclass_implements_read() -> None:
    class ConcreteReader(Reader[str]):
        def read(self) -> str:
            return "data"

    assert ConcreteReader().read() == "data"
