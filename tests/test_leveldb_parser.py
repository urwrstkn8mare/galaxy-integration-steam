from leveldb_parser import LevelDbParser
import pytest
import os
import hashlib
import json

PARSED_LVLDB_UTF8_MD5 = b'q\xf6\xbd~\x14\x8c\x01\x17vl\x14\xe9"\x83f\xd3'
PARSED_LVLDB_UTF16LE_MD5 = b'\xb3G\xa4\x818a\xa7\x8b<\xcf\xcd\x08\xa0\xedQ\xf8'
RETRIEVED_JSONS_MD5 = b'\xff]\xf6\x9d\xd2\xdcR\xf6\xa4\\\xc6&qZ\xaf\x80'
USER_JSON_START_UTF16 = 5703
USER_JSON_START_UTF8 = 23259
USER_JSON_END_UTF16 = -1
USER_JSON_END_UTF8 = -1


@pytest.mark.asyncio
async def test_parser_initialization_ok():
    LevelDbParser(12345678)

@pytest.mark.asyncio
async def test_parser_initialization_fail():
    with pytest.raises(TypeError):
        LevelDbParser()

@pytest.mark.asyncio
async def test_read_db_file_utf8():
    level_db_parser = LevelDbParser(12345678)
    db_log_directory = os.path.dirname(os.path.abspath(__file__))
    open_db_log = level_db_parser._read_db_log_file(db_log_directory)

    open_db_log = open_db_log.encode('utf-8')
    open_db_log = hashlib.md5(open_db_log)
    open_db_log = open_db_log.digest()

    assert open_db_log == PARSED_LVLDB_UTF8_MD5

@pytest.mark.asyncio
async def test_read_db_file_utf16():
    level_db_parser = LevelDbParser(12345678)
    db_log_directory = os.path.dirname(os.path.abspath(__file__))
    open_db_log = level_db_parser._read_db_log_file(db_log_directory, 'utf-16-le')

    open_db_log = open_db_log.encode('utf-16-le')
    open_db_log = hashlib.md5(open_db_log)
    open_db_log = open_db_log.digest()

    assert open_db_log == PARSED_LVLDB_UTF16LE_MD5

@pytest.mark.asyncio
async def test_meta_miniprofile_pair_utf8():
    level_db_parser = LevelDbParser(12345678)
    db_log_directory = os.path.dirname(os.path.abspath(__file__))
    open_db_log = level_db_parser._read_db_log_file(db_log_directory, 'utf-8')
    user_json_start, user_json_end, encoding = level_db_parser._find_last_meta_miniprofile_pair(open_db_log)

    assert user_json_start == USER_JSON_START_UTF8 and user_json_end == USER_JSON_END_UTF8

@pytest.mark.asyncio
async def test_meta_miniprofile_pair_utf16():
    level_db_parser = LevelDbParser(12345678)
    db_log_directory = os.path.dirname(os.path.abspath(__file__))
    open_db_log = level_db_parser._read_db_log_file(db_log_directory, 'utf-16-le')
    user_json_start, user_json_end, encoding = level_db_parser._find_last_meta_miniprofile_pair(open_db_log)

    assert user_json_start == USER_JSON_START_UTF16 and user_json_end == USER_JSON_END_UTF16

@pytest.mark.asyncio
async def test_retrieve_jsons():
    level_db_parser = LevelDbParser(12345678)
    db_log_directory = os.path.dirname(os.path.abspath(__file__))
    open_db_log = level_db_parser._read_db_log_file(db_log_directory, 'utf-16-le')
    user_json_start, user_json_end, encoding = level_db_parser._find_last_meta_miniprofile_pair(open_db_log)

    collections_list = level_db_parser._retrieve_jsons(open_db_log, user_json_start, user_json_end)

    collections_list = json.dumps(collections_list)
    collections_list = collections_list.encode('utf-16-le')
    hash = hashlib.md5(collections_list)

    assert hash.digest() == RETRIEVED_JSONS_MD5
