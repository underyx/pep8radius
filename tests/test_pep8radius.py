from util import *

try:
    os.mkdir(TEMP_DIR)
except OSError:
    pass

try:
    os.mkdir(SUBTEMP_DIR)
except OSError:
    pass


class TestRadius(TestCase):

    def __init__(self, *args, **kwargs):
        self.original_dir = os.getcwd()
        os.chdir(TEMP_DIR)
        self.using_vc = self.init_vc()
        super(TestRadius, self).__init__(*args, **kwargs)

    def tearDown(self):
        os.chdir(self.original_dir)

    def init_vc(self):
        self.delete_repo()
        success = self.create_repo()
        committed = self._save_and_commit('a=1;', 'a.py')
        os.chdir(self.original_dir)
        return success

    def setUp(self):
        os.chdir(TEMP_DIR)
        success = self.init_vc()
        if not success:
            raise SkipTest("%s not available" % self.vc)

    @staticmethod
    def _save(contents, f):
        with from_dir(TEMP_DIR):
            with open(f, 'w') as f1:
                f1.write(contents)

    @staticmethod
    def get_diff_many(modified, expected, files):
        return ''.join(get_diff(*mef)
                       for mef in zip(modified, expected, files))

    def check(self, original, modified, expected,
              test_name='check', options=None,
              directory=TEMP_DIR):
        """Modify original to modified, and check that pep8radius
        turns this into expected."""
        os.chdir(directory)
        temp_file = os.path.join(TEMP_DIR, 'temp.py')

        options = parse_args(options)

        # TODO remove this color hack, and actually test printing color diff
        options.no_color = True

        with open(temp_file, 'w') as f:
            f.write(original)
        committed = self.successfully_commit_files([temp_file],
                                                   commit=test_name)

        with open(temp_file, 'w') as f:
            f.write(modified)

        options.verbose = 1
        r = Radius.new(vc=self.vc, options=options)
        with captured_output() as (out, err):
            r.pep8radius()
        self.assertIn('would fix', out.getvalue())
        self.assertNotIn('@@', out.getvalue())
        options.verbose = 0

        options.diff = True
        r = Radius.new(vc=self.vc, options=options)
        with captured_output() as (out, err):
            r.pep8radius()
        exp_diff = get_diff(modified, expected, temp_file)
        self.assert_equal(out.getvalue(), exp_diff, test_name)
        options.diff = False

        options.in_place = True
        r = Radius.new(vc=self.vc, options=options)
        # Run pep8radius
        r.pep8radius()

        with open(temp_file, 'r') as f:
            result = f.read()
        self.assert_equal(result, expected, test_name)

        # Run pep8radius again, it *should* be that this doesn't do anything.
        with captured_output() as (out, err):
            pep8radius_main(options, vc=self.vc)
        self.assertEqual(out.getvalue(), '')

        with open(temp_file, 'r') as f:
            result = f.read()
        self.assert_equal(result, expected, test_name)

    def assert_equal(self, result, expected, test_name):
        """like assertEqual but with a nice diff output if not equal"""
        self.assertEqual(result, expected,
                         get_diff(expected, result, test_name,
                                  'expected', 'result'))


class MixinTests:

    """All Radius tests are placed in this class"""

    def test_one_line(self):
        original = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=2; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        modified = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=42; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        expected = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na = 1\nb = 42\nc = 3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        self.check(original, modified, expected, 'test_one_line')

    def test_one_line_from_subdirectory(self):
        original = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=2; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        modified = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=42; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        expected = 'def poor_indenting():\n  a = 1\n  b = 2\n  return a + b\n\nfoo = 1; bar = 2; print(foo * bar)\na = 1\nb = 42\nc = 3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        self.check(original, modified, expected, 'test_one_line',
                   directory=SUBTEMP_DIR)

    def test_with_docformatter(self):
        original = 'def poor_indenting():\n  """       Great function"""\n  a = 1\n  b = 2\n  return a + b\n\n\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=2; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        modified = 'def poor_indenting():\n  """  Very great function"""\n  a = 1\n  b = 2\n  return a + b\n\n\n\nfoo = 1; bar = 2; print(foo * bar)\na=1; b=42; c=3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        expected = 'def poor_indenting():\n  """  Very great function"""\n  a = 1\n  b = 2\n  return a + b\n\n\n\nfoo = 1; bar = 2; print(foo * bar)\na = 1\nb = 42\nc = 3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        self.check(original, modified, expected, 'test_without_docformatter')

        expected = 'def poor_indenting():\n  """Very great function."""\n  a = 1\n  b = 2\n  return a + b\n\n\n\nfoo = 1; bar = 2; print(foo * bar)\na = 1\nb = 42\nc = 3\nd=7\n\ndef f(x = 1, y = 2):\n    return x + y\n'
        self.check(original, modified, expected,
                   'test_with_docformatter', ['--docformatter'])

    def test_bad_rev(self):
        os.chdir(TEMP_DIR)
        # TODO for some reason this isn't capturing the output!
        with captured_output() as (out, err):
            self.assertRaises(CalledProcessError,
                              lambda x: Radius.new(rev=x, vc=self.vc),
                              'random_junk_sha')
        os.chdir(self.original_dir)

    def test_earlier_revision(self):
        if self.vc == 'bzr':
            raise SkipTest()

        start = self._save_and_commit('a=1;', 'AAA.py')
        self.checkout('ter', create=True)
        self._save_and_commit('b=1;', 'BBB.py')
        tip = self._save_and_commit('c=1;', 'CCC.py')
        self._save('c=1', 'CCC.py')

        args = parse_args(['--diff', '--no-color'])
        r = Radius.new(rev=start, options=args, vc=self.vc)
        with captured_output() as (out, err):
            r.pep8radius()
        diff = out.getvalue()

        files = [os.path.join(TEMP_DIR, f) for f in ['BBB.py', 'CCC.py']]

        exp_diff = self.get_diff_many(['b=1;', 'c=1'],
                                      ['b = 1\n', 'c = 1\n'],
                                      files)
        self.assert_equal(diff, exp_diff, 'earlier_revision')

        # TODO test the diff is correct


class TestRadiusGit(TestRadius, MixinGit, MixinTests):
    vc = 'git'


class TestRadiusHg(TestRadius, MixinHg, MixinTests):
    vc = 'hg'


class TestRadiusBzr(TestRadius, MixinBzr, MixinTests):
    vc = 'bzr'


if __name__ == '__main__':
    test_main()
