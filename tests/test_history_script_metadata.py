import struct
import unittest
from history_script_metadata import action,replacement_prompt,available_replacement


class StoryScriptMetadataTests(unittest.TestCase):
    def fixture(self):
        ram=bytearray(256)
        # Battle(17, 0): select side 0, reserve slot 1. Option -w has one argument.
        words=(0x00080201,0x0a,0x10a,0x00017708,0x10a,0)
        struct.pack_into('<4s3I',ram,0,b'GSAC',16,len(words)*4,10004)
        struct.pack_into('<6I',ram,16,*words)
        struct.pack_into('<4s3I',ram,128,b'GSDT',16,8,0)
        struct.pack_into('<2i',ram,144,17,0)
        return ram

    def test_decodes_constants_and_skips_option_arguments(self):
        event=action(self.fixture(),0,128)
        self.assertEqual(event['replacements'],[dict(side=0,slot=1,address=16)])
        self.assertEqual(event['commands'][0]['args'][0]['integer'],17)
        self.assertEqual(event['commands'][0]['options'][0]['flag'],'w')

    def test_active_partner_is_not_a_reserve(self):
        event=action(self.fixture(),0,128)
        self.assertFalse(available_replacement(event,{0:(0,1)}))
        self.assertTrue(available_replacement(event,{0:(0,)}))

    def test_dialogue_and_skill_prompts_are_not_replacements(self):
        self.assertFalse(replacement_prompt(0x11))
        self.assertFalse(replacement_prompt(0x81))
        self.assertTrue(replacement_prompt(0x41))
        self.assertFalse(replacement_prompt(0x40))

    def test_bad_pool_reference_is_refused(self):
        ram=self.fixture();struct.pack_into('<I',ram,20,0xff0a)
        with self.assertRaises(ValueError):action(ram,0,128)

    def test_truncated_chunk_is_refused(self):
        ram=self.fixture();struct.pack_into('<I',ram,8,256)
        with self.assertRaises(ValueError):action(ram,0,128)


if __name__=='__main__':unittest.main()
