# ⁻*- coding: utf-8 -*-
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License version 3 for
# more details.
#
# You should have received a copy of the GNU General Public License version 3
# along with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (c) 2016 Valentin Samir
"""Tests module for utils"""
from django.test import TestCase

import six

from cas_server import utils


class CheckPasswordCase(TestCase):
    """Tests for the utils function `utils.check_password`"""

    def setUp(self):
        """Generate random bytes string that will be used ass passwords"""
        self.password1 = utils.gen_saml_id()
        self.password2 = utils.gen_saml_id()
        if not isinstance(self.password1, bytes):  # pragma: no cover executed only in python3
            self.password1 = self.password1.encode("utf8")
            self.password2 = self.password2.encode("utf8")

    def test_setup(self):
        """check that generated password are bytes"""
        self.assertIsInstance(self.password1, bytes)
        self.assertIsInstance(self.password2, bytes)

    def test_plain(self):
        """test the plain auth method"""
        self.assertTrue(utils.check_password("plain", self.password1, self.password1, "utf8"))
        self.assertFalse(utils.check_password("plain", self.password1, self.password2, "utf8"))

    def test_plain_unicode(self):
        """test the plain auth method with unicode input"""
        self.assertTrue(
            utils.check_password(
                "plain",
                self.password1.decode("utf8"),
                self.password1.decode("utf8"),
                "utf8"
            )
        )
        self.assertFalse(
            utils.check_password(
                "plain",
                self.password1.decode("utf8"),
                self.password2.decode("utf8"),
                "utf8"
            )
        )

    def test_crypt(self):
        """test the crypt auth method"""
        salts = ["$6$UVVAQvrMyXMF3FF3", "aa"]
        hashed_password1 = []
        for salt in salts:
            if six.PY3:
                hashed_password1.append(
                    utils.crypt.crypt(
                        self.password1.decode("utf8"),
                        salt
                    ).encode("utf8")
                )
            else:
                hashed_password1.append(utils.crypt.crypt(self.password1, salt))

        for hp1 in hashed_password1:
            self.assertTrue(utils.check_password("crypt", self.password1, hp1, "utf8"))
            self.assertFalse(utils.check_password("crypt", self.password2, hp1, "utf8"))

        with self.assertRaises(ValueError):
            utils.check_password("crypt", self.password1, b"$truc$s$dsdsd", "utf8")

    def test_ldap_password_valid(self):
        """test the ldap auth method with all the schemes"""
        salt = b"UVVAQvrMyXMF3FF3"
        schemes_salt = [b"{SMD5}", b"{SSHA}", b"{SSHA256}", b"{SSHA384}", b"{SSHA512}"]
        schemes_nosalt = [b"{MD5}", b"{SHA}", b"{SHA256}", b"{SHA384}", b"{SHA512}"]
        hashed_password1 = []
        for scheme in schemes_salt:
            hashed_password1.append(
                utils.LdapHashUserPassword.hash(scheme, self.password1, salt, charset="utf8")
            )
        for scheme in schemes_nosalt:
            hashed_password1.append(
                utils.LdapHashUserPassword.hash(scheme, self.password1, charset="utf8")
            )
        hashed_password1.append(
            utils.LdapHashUserPassword.hash(
                b"{CRYPT}",
                self.password1,
                b"$6$UVVAQvrMyXMF3FF3",
                charset="utf8"
            )
        )
        for hp1 in hashed_password1:
            self.assertIsInstance(hp1, bytes)
            self.assertTrue(utils.check_password("ldap", self.password1, hp1, "utf8"))
            self.assertFalse(utils.check_password("ldap", self.password2, hp1, "utf8"))

    def test_ldap_password_fail(self):
        """test the ldap auth method with malformed hash or bad schemes"""
        salt = b"UVVAQvrMyXMF3FF3"
        schemes_salt = [b"{SMD5}", b"{SSHA}", b"{SSHA256}", b"{SSHA384}", b"{SSHA512}"]
        schemes_nosalt = [b"{MD5}", b"{SHA}", b"{SHA256}", b"{SHA384}", b"{SHA512}"]

        # first try to hash with bad parameters
        with self.assertRaises(utils.LdapHashUserPassword.BadScheme):
            utils.LdapHashUserPassword.hash(b"TOTO", self.password1)
        for scheme in schemes_nosalt:
            with self.assertRaises(utils.LdapHashUserPassword.BadScheme):
                utils.LdapHashUserPassword.hash(scheme, self.password1, salt)
        for scheme in schemes_salt:
            with self.assertRaises(utils.LdapHashUserPassword.BadScheme):
                utils.LdapHashUserPassword.hash(scheme, self.password1)
        with self.assertRaises(utils.LdapHashUserPassword.BadSalt):
            utils.LdapHashUserPassword.hash(b'{CRYPT}', self.password1, b"$truc$toto")

        # then try to check hash with bad hashes
        with self.assertRaises(utils.LdapHashUserPassword.BadHash):
            utils.check_password("ldap", self.password1, b"TOTOssdsdsd", "utf8")
        for scheme in schemes_salt:
            with self.assertRaises(utils.LdapHashUserPassword.BadHash):
                utils.check_password("ldap", self.password1, scheme + b"dG90b3E8ZHNkcw==", "utf8")

    def test_hex(self):
        """test all the hex_HASH method: the hashed password is a simple hash of the password"""
        hashes = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
        hashed_password1 = []
        for hash in hashes:
            hashed_password1.append(
                ("hex_%s" % hash, getattr(utils.hashlib, hash)(self.password1).hexdigest())
            )
        for (method, hp1) in hashed_password1:
            self.assertTrue(utils.check_password(method, self.password1, hp1, "utf8"))
            self.assertFalse(utils.check_password(method, self.password2, hp1, "utf8"))

    def test_bad_method(self):
        """try to check password with a bad method, should raise a ValueError"""
        with self.assertRaises(ValueError):
            utils.check_password("test", self.password1, b"$truc$s$dsdsd", "utf8")


class UtilsTestCase(TestCase):
    """tests for some little utils functions"""
    def test_import_attr(self):
        """
            test the import_attr function. Feeded with a dotted path string, it should
            import the dotted module and return that last componend of the dotted path
            (function, class or variable)
        """
        with self.assertRaises(ImportError):
            utils.import_attr('toto.titi.tutu')
        with self.assertRaises(AttributeError):
            utils.import_attr('cas_server.utils.toto')
        with self.assertRaises(ValueError):
            utils.import_attr('toto')
        self.assertEqual(
            utils.import_attr('cas_server.default_app_config'),
            'cas_server.apps.CasAppConfig'
        )
        self.assertEqual(utils.import_attr(utils), utils)

    def test_update_url(self):
        """
            test the update_url function. Given an url with possible GET parameter and a dict
            the function build a url with GET parameters updated by the dictionnary
        """
        url1 = utils.update_url(u"https://www.example.com?toto=1", {u"tata": u"2"})
        url2 = utils.update_url(b"https://www.example.com?toto=1", {b"tata": b"2"})
        self.assertEqual(url1, u"https://www.example.com?tata=2&toto=1")
        self.assertEqual(url2, u"https://www.example.com?tata=2&toto=1")

        url3 = utils.update_url(u"https://www.example.com?toto=1", {u"toto": u"2"})
        self.assertEqual(url3, u"https://www.example.com?toto=2")
