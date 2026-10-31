from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "planner", password="A-long-test-password!2026"
        )

    def test_public_landing_and_all_evidence_routes_require_login(self):
        self.assertContains(self.client.get("/"), "Better planning")
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})
        for path in [
            "/workspace/",
            "/workspace/overview/",
            "/national-policy-evidence/",
            "/national-policy-evidence/crop/",
            "/national-policy-evidence/note/?download=text",
            "/district-crop-statistics/",
            "/workbook-evidence/?download=csv",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 302)
                self.assertTrue(
                    self.client.get(path)["Location"].startswith("/accounts/login/")
                )

    def test_landing_is_complete_and_uses_local_responsive_assets(self):
        from django.contrib.staticfiles import finders
        from html.parser import HTMLParser

        response = self.client.get("/")
        markup = response.content.decode()
        for section in ("about", "features", "how-it-works", "evidence-principles"):
            self.assertContains(response, f'id="{section}"')
        self.assertContains(response, 'fetchpriority="high"')
        self.assertContains(response, "Evidence views require an APASA account")
        self.assertNotIn("r2.dev", markup)
        self.assertContains(response, "hero-scene__vehicle")
        self.assertContains(response, "hero-scene__wordmark")
        self.assertContains(response, "tractor-3d-960.webp")
        self.assertContains(response, "foreground-crops-960.webp")
        self.assertContains(response, "animations.css")
        self.assertNotIn("tractor-dust.png", markup)

        class Assets(HTMLParser):
            paths = []
            def handle_starttag(self, tag, attributes):
                values = dict(attributes)
                if tag in {"img", "script", "use"}:
                    self.paths.append(values.get("src", values.get("href", "")))
                if tag == "link":
                    self.paths.append(values.get("href", ""))
                if tag == "img":
                    self.assert_dimensions = "width" in values and "height" in values
        assets = Assets()
        assets.feed(markup)
        self.assertTrue(assets.assert_dimensions)
        for path in assets.paths:
            self.assertTrue(path.startswith("/static/"), path)
            self.assertIsNotNone(finders.find(path.removeprefix("/static/").split("#")[0]), path)
        for width in (640, 960, 1440):
            self.assertIsNotNone(finders.find(f"accounts/landing/landscape-rwanda-{width}.webp"))

    def test_login_failure_success_and_safe_next(self):
        response = self.client.post(
            "/accounts/login/", {"username": "planner", "password": "wrong"}
        )
        self.assertContains(response, "not accepted")
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "planner",
                "password": "A-long-test-password!2026",
                "next": "https://evil.example/",
            },
        )
        self.assertRedirects(response, "/workspace/", fetch_redirect_response=False)
        self.assertContains(
            self.client.get("/national-policy-evidence/"), "National Policy Evidence"
        )
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
        self.assertRedirects(
            self.client.post("/accounts/logout/"), "/", fetch_redirect_response=False
        )
        self.assertEqual(self.client.get("/workbook-evidence/").status_code, 302)

    def test_login_is_focused_and_preserves_username_on_generic_failure(self):
        response = self.client.get("/accounts/login/?next=/workspace/overview/")
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, 'aria-controls="id_password"')
        self.assertNotContains(response, 'class="workspace-nav"')
        self.assertNotContains(response, 'class="workspace-header"')
        messages = []
        for username in ("planner", "unknown-account"):
            failed = self.client.post(
                "/accounts/login/",
                {"username": username, "password": "wrong", "next": "/workspace/overview/"},
            )
            self.assertContains(failed, f'value="{username}"')
            self.assertContains(failed, 'name="next" value="/workspace/overview/"')
            messages.append(failed.context["form"].non_field_errors())
        self.assertEqual(messages[0], messages[1])

    def test_role_landing_and_csrf_protection(self):
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get("/workspace/"),
            "/planning/",
            fetch_redirect_response=False,
        )
        self.user.groups.add(Group.objects.create(name="District agriculture officer"))
        self.assertRedirects(
            self.client.get("/workspace/"),
            "/planning/",
            fetch_redirect_response=False,
        )
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            csrf_client.post(
                "/accounts/login/", {"username": "planner", "password": "x"}
            ).status_code,
            403,
        )

    @override_settings(DEBUG=True)
    def test_demo_provisioning_is_repeatable_and_preserves_password(self):
        call_command("provision_accounts", demo=True, stdout=StringIO())
        user = get_user_model().objects.get(username="policymaker")
        self.assertTrue(user.check_password("ApasaPolicyDemo!2026"))
        user.set_password("ChangedPassword!2026")
        user.save()
        call_command("provision_accounts", demo=True, stdout=StringIO())
        self.assertTrue(
            get_user_model()
            .objects.get(pk=user.pk)
            .check_password("ChangedPassword!2026")
        )

    @override_settings(DEBUG=False)
    def test_production_refuses_demo_accounts(self):
        with self.assertRaises(CommandError):
            call_command("provision_accounts", demo=True)
