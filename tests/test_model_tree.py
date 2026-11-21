import pytest
from types import SimpleNamespace

from featoolbox.model import Model, ModelTree, TreeNode


def test_find_searches_only_immediate_children() -> None:
    tree = ModelTree()
    root = tree.tree
    first_branch = TreeNode("first", parent=root)
    shallow_match = TreeNode("target", parent=root)
    deep_match = TreeNode("target", parent=first_branch)
    root.children.extend([first_branch, shallow_match])
    first_branch.children.append(deep_match)

    assert tree.find("target", root.name) is shallow_match
    assert tree.find("target", first_branch.name) is deep_match


def test_find_returns_none_when_name_is_missing() -> None:
    tree = ModelTree()

    assert tree.find("missing", tree.tree.name) is None


def test_indexing_returns_child_data_and_allows_nested_access() -> None:
    tree = ModelTree()
    data = SimpleNamespace(name="SOLID185")
    tree.insert("Child Name", "Element Types", data)

    assert tree["Element Types"]["Child Name"] is data


def test_indexing_missing_child_raises_key_error() -> None:
    tree = ModelTree()

    with pytest.raises(KeyError, match="Tree node 'missing'"):
        tree["Element Types"]["missing"]


def test_insert_attaches_node_to_parent_and_returns_it() -> None:
    tree = ModelTree()
    parent = tree.tree
    data = SimpleNamespace(midx=99)

    inserted = tree.insert("child", parent.name, data)

    assert inserted.name == "child"
    assert inserted.parent is parent
    assert inserted.data is data
    assert data.midx == 1
    assert inserted in parent.children
    assert tree.find("child", parent.name) is inserted

    second_data = SimpleNamespace(midx=99)
    tree.insert("second", parent.name, second_data)
    assert second_data.midx == 2

    explicit_data = SimpleNamespace(midx=99)
    tree.insert("explicit", parent.name, explicit_data, midx=12)
    assert explicit_data.midx == 12

    next_data = SimpleNamespace(midx=99)
    tree.insert("next", parent.name, next_data)
    assert next_data.midx == 13


def test_insert_rejects_midx_without_data() -> None:
    tree = ModelTree()

    with pytest.raises(ValueError, match="without node data"):
        tree.insert("item", "Root", midx=3)


def test_add_element_type_forwards_tree_options() -> None:
    model = Model.__new__(Model)
    model.model_tree = ModelTree()
    etype = SimpleNamespace(name="SOLID185", midx=0, ignore_at_execution=False)

    model.add_element_type(
        etype,
        visible=False,
        send_solver=False,
    )

    node = model.model_tree.find("SOLID185", "Element Types")
    assert node is not None
    assert node.visible is False
    assert node.send_solver is False
    assert etype.ignore_at_execution is False


def test_add_element_type_uses_tree_option_defaults() -> None:
    model = Model.__new__(Model)
    model.model_tree = ModelTree()
    etype = SimpleNamespace(name="SOLID186", midx=0, ignore_at_execution=False)

    model.add_element_type(etype)

    node = model.model_tree.find("SOLID186", "Element Types")
    assert node is not None
    assert node.visible is True
    assert node.send_solver is True


def test_add_element_type_rejects_ignore_at_execution() -> None:
    model = Model.__new__(Model)
    model.model_tree = ModelTree()
    etype = SimpleNamespace(name="SOLID187", midx=0, ignore_at_execution=False)

    with pytest.raises(TypeError, match="ignore_at_execution"):
        model.add_element_type(etype, ignore_at_execution=True)


def test_remove_detaches_child_from_parent() -> None:
    tree = ModelTree()
    parent = tree.tree
    child = tree.insert("child", parent.name)
    grandchild = tree.insert("grandchild", child.name)

    tree.remove("child", parent.name)

    assert child not in parent.children
    assert child.parent is None
    assert grandchild.parent is child
    assert tree.find("child", parent.name) is None


def test_remove_raises_for_missing_child() -> None:
    tree = ModelTree()

    with pytest.raises(KeyError, match="Tree node 'missing'"):
        tree.remove("missing", tree.tree.name)


def test_max_id_uses_child_data_and_returns_zero_for_empty_parent() -> None:
    tree = ModelTree()
    parent = tree.insert("nested group", tree.tree.name)
    tree.insert("first", parent.name, SimpleNamespace(midx=2))
    tree.insert("second", parent.name, SimpleNamespace(midx=7))
    tree.insert("third", parent.name, SimpleNamespace(midx=4))
    parent.children[0].data.midx = 2
    parent.children[1].data.midx = 7
    parent.children[2].data.midx = 4

    assert tree.max_id("nested group") == 7
    assert tree.max_id("Materials") == 0


def test_max_id_raises_when_parent_is_missing() -> None:
    tree = ModelTree()

    with pytest.raises(KeyError, match="Tree node 'missing'"):
        tree.max_id("missing")


def test_string_representation_shows_names_and_midx_in_ascii_tree() -> None:
    tree = ModelTree()
    tree.tree = TreeNode("Root")
    parent = tree.insert("Node Sets", tree.tree.name)
    tree.insert("set_a", parent.name, SimpleNamespace(midx=7))
    tree.insert("set_b", parent.name)

    assert str(tree) == (
        "Root\n"
        "`-- Node Sets\n"
        "    |-- set_a (midx=1)\n"
        "    `-- set_b"
    )


def test_string_representation_hides_invisible_nodes_and_subtrees() -> None:
    tree = ModelTree()
    tree.tree = TreeNode("Root")
    tree.insert("first", "Root")
    hidden = tree.insert("hidden", "Root", visible=False)
    tree.insert("hidden child", hidden.name)
    tree.insert("last", "Root")

    assert str(tree) == "Root\n|-- first\n`-- last"


def test_tree_nodes_have_independent_children() -> None:
    first = TreeNode("first")
    second = TreeNode("second")
    child = TreeNode("child")

    first.children.append(child)

    assert second.children == []
