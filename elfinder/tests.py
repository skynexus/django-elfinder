from django.test import TestCase
from django.core.urlresolvers import reverse
from elfinder.models import FileCollection, Directory, File
from elfinder.volume_drivers.model_driver import ModelVolumeDriver
import json
import logging


class elFinderTest(TestCase):
    """ Tests basic template functionality.
    """
    fixtures = ['testdata.json']

    def setUp(self):
        # Disable logging when running tests
        logging.disable(logging.CRITICAL)

    def test_elfinder_index(self):
        """ Ensures that the elfinder.html template is used, and coll_id is in
            the template's context.
        """
        self.collection = FileCollection.objects.get(pk=1)
        response = self.client.get(reverse('elfinder_index',
                                            args=[self.collection.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'elfinder.html')
        self.assertEqual(response.context['coll_id'], self.collection.id)


class elFinderFileCollectionTest(TestCase):
    """ Tests functions related to creating/editing FileCollection objects.
    """
    def setUp(self):
        # Disable logging when running tests
        logging.disable(logging.CRITICAL)

    def test_new_filecollection(self):
        new_coll = FileCollection(name='test')
        new_coll.save()
        # Make sure the root dir was created
        volume = ModelVolumeDriver(new_coll.id)
        volume_info = volume.get_info('')
        self.assertEqual(volume_info['name'], 'test')


class elFinderCmdTest(TestCase):
    """ Base class for testing connector commands.

        Each command has its own class which extends this, and adds one
        or more specific tests for that command. This lets each command
        test valid and invalid requests.
    """
    fixtures = ['testdata.json']

    def setUp(self):
        # Disable logging when running tests
        logging.disable(logging.CRITICAL)
        self.collection = FileCollection.objects.get(pk=1)
        self.volume = ModelVolumeDriver(1)

    def get_command_response(self, variables={}):
        """ Helper function to issue commands to the connector.
        """
        return self.client.get(reverse('elfinder_connector',
                                        args=[self.collection.id]),
                                        variables)

    def get_json_response(self, variables={}, fail_on_error=True):
        """ Helper function - calls get_command_response and ensures the
            response is a JSON object. Adds the deserialised JSON object
            to the response.

            If fail_on_error is true and the response includes an 'error'
            object, the test will fail.
        """
        response = self.get_command_response(variables)
        response.json = json.loads(response.content)

        if fail_on_error:
            self.assertFalse('error' in response.json,
                'JSON Response contained an error: ' + response.content)
        return response


class elFinderInvalidCmds(elFinderCmdTest):
    def test_unknown_cmd(self):
        response = self.get_json_response({'cmd': 'invalid_cmd_test'}, False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Unknown command')

    def test_no_cmd(self):
        response = self.get_json_response({}, False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'No command specified')


class elFinderOpenCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'open'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_open_empty_target(self):
        vars = ({'cmd': 'open',
                 'target': ''})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_valid_open_empty_target_with_tree(self):
        vars = ({'cmd': 'open',
                 'target': '',
                 'tree': 1})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_valid_open_with_tree(self):
        vars = ({'cmd': 'open',
                 'target': 'fc1_d2',
                 'tree': 1})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_valid_open_with_init(self):
        vars = ({'cmd': 'open',
                 'target': 'fc1_d2',
                 'tree': 1,
                 'init': 1})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['api'], '2.0')


class elFinderMkdirCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'mkdir'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_mkdir(self):
        vars = ({'cmd': 'mkdir',
                 'target': 'fc1_d1',
                 'name': 'new dir'})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_invalid_target(self):
        response = self.get_json_response({'cmd': 'mkdir',
                                           'target': 'does-not-exist',
                                           'name': 'new dir'},
                                           fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        expected_error = 'Invalid target hash: '
        self.assertTrue(response.json['error'].startswith(expected_error))

    def test_duplicate_dir_name(self):
        """ Try to create two dirs with the same name and ensure it fails.
        """
        vars = ({'cmd': 'mkdir',
                 'target': 'fc1_d1',
                 'name': 'dupe_dir_test'})
        response = self.get_json_response(vars)
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'],
                         'Directory with this Name and Parent already exists.')


class elFinderMkfileCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'mkdir'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_mkfile(self):
        vars = ({'cmd': 'mkfile',
                 'target': 'fc1_d1',
                 'name': 'test file.txt'})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_duplicate_filename(self):
        """ Try to create two files with the same name and ensure it fails.
        """
        vars = ({'cmd': 'mkfile',
                 'target': 'fc1_d1',
                 'name': 'dupe_filename_test'})
        response = self.get_json_response(vars)
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'],
                         'File with this Name and Parent already exists.')


class elFinderParentsCmd(elFinderCmdTest):
    def test_valid_parents(self):
        vars = {'cmd': 'parents',
                'target': 'fc1_d1'}
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)


class elFinderTreeCmd(elFinderCmdTest):
    def test_valid_tree(self):
        vars = {'cmd': 'tree',
                'target': 'fc1_d1'}
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)


class elFinderRenameCmd(elFinderCmdTest):
    def test_valid_name(self):
        vars = {'cmd': 'rename',
                'target': 'fc1_f1',
                'name': 'new_name.html'}
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)
        added = response.json['added']
        removed = response.json['removed']
        self.assertEqual(added[0]['name'], 'new_name.html')
        self.assertEqual(removed[0], 'fc1_f1')

    def test_missing_name(self):
        vars = {'cmd': 'rename',
                'target': 'fc1_f1'}
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.json['error'], 'Invalid arguments')


class elFinderFileCmd(elFinderCmdTest):
    def setUp(self):
        super(elFinderFileCmd, self).setUp()
        self.file = File.objects.get(pk=1)

    def test_valid_file(self):
        vars = {'cmd': 'file',
                'target': 'fc1_f1'}
        response = self.get_command_response(vars)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'read_file.html')
        self.assertEqual(response.context['file'], self.file)

    def test_invalid_file(self):
        vars = ({'cmd': 'file',
                 'target': 'fc1_f1234'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Could not open target')

    def test_invalid_targets(self):
        for target in ['bad-target', 'fc1_bad', 'fc1_', 'fc1_x1']:
            vars = {'cmd': 'file',
                    'target': target}
            response = self.get_json_response(vars, fail_on_error=False)
            self.assertEqual(response.status_code, 200)
            expected_error = 'Invalid target hash: '
            self.assertTrue(response.json['error'].startswith(expected_error))
