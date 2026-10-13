"""Portable format checks; no original magazine files required."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from Crypto.Cipher import Blowfish
from archive.djvu import decode_data


def chunk(tag, payload):
    return tag + struct.pack('>I',len(payload)) + payload + (b'\0' if len(payload)%2 else b'')


class FormatTests(unittest.TestCase):
    def test_encrypted_info_recovers_standard_page(self):
        info=bytes.fromhex('02580320001901001601')
        key=hashlib.md5(b'secureDVD_UIDLizardTech_DVDKey_Internal_Salt').digest()
        iv=hashlib.md5(b'Blowfish'+struct.pack('>I',7)).digest()[:8]
        cipher=Blowfish.new(key,Blowfish.MODE_CBC,iv).encrypt(info+b'\0'*6)
        secured=chunk(b'FORM',b'DJVU'+chunk(b'CELX',b'INFO'+struct.pack('>II',10,7)+cipher))
        original=b'SDJV'+chunk(b'FORM',b'DJVM'+secured)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'pages'
            self.assertEqual(decode_data(original,out),1)
            self.assertEqual((out/'page-0001.djvu').read_bytes(),b'AT&T'+chunk(b'FORM',b'DJVU'+chunk(b'INFO',info)))

    def test_invalid_container_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for data in (b'not a document',b'SDJVFORM'+b'\xff'*4+b'DJVM'):
                with self.subTest(data=data),self.assertRaises(ValueError):
                    decode_data(data,Path(tmp)/'pages')
