from .. import docker_bump


def test_version():
    assert docker_bump.__version__ == "0.1.0"


def test_maven_tag_match():
    assert docker_bump._filter_maven_tags(
        ["3.6.3-adoptopenjdk-11", "buster", "3.6.3-adoptopenjdk-12"]
    ) == ["3.6.3-adoptopenjdk-11"]
