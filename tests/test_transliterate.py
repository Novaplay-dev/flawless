from flawless.transliterate import cyrillic_to_latin


def test_basic_sentence():
    assert cyrillic_to_latin("Добар дан, како сте?") == "Dobar dan, kako ste?"


def test_digraphs():
    assert cyrillic_to_latin("Љубав и њива у Џепу") == "Ljubav i njiva u Džepu"


def test_all_caps_digraphs():
    assert cyrillic_to_latin("ЉУБАВ") == "LJUBAV"


def test_latin_passthrough():
    assert cyrillic_to_latin("hello world 123!") == "hello world 123!"


def test_mixed():
    assert cyrillic_to_latin("čačak и Чачак") == "čačak i Čačak"
