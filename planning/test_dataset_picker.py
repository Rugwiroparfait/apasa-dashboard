"""Dataset choice works with empty databases, repeated loading and source changes."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from .tests import PlanningFixture
from .models import SourceBatch, IndicatorVersion, Assessment, State


class DatasetPickerTests(PlanningFixture):
    def test_empty_picker_is_actionable_and_get_does_not_seed(self):
        self.report.delete()
        self.batch.delete()
        before = IndicatorVersion.objects.count()
        response = self.client.get(reverse('planning:assessment-create'))
        self.assertContains(response, 'Start with a dataset')
        self.assertContains(response, 'Use demonstration datasets')
        self.assertNotContains(response, 'id="dataset-select"')
        self.assertEqual(SourceBatch.objects.count(), 0)
        self.assertEqual(IndicatorVersion.objects.count(), before)

    def test_explicit_demo_load_is_repeatable_and_keeps_official_records(self):
        response = self.client.post(reverse('planning:load-comparison-demos'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SourceBatch.objects.filter(status=State.DEMO).count(), 2)
        self.assertEqual(IndicatorVersion.objects.filter(status=State.DEMO).count(), 2)
        self.assertEqual(Assessment.objects.count(), 1)
        page = self.client.get(response.url)
        self.assertContains(page, '2. Match the target and observation')
        self.assertEqual(page.context['dataset'].title, 'MOCKED · National demonstration')
        self.assertEqual(len(page.context['form'].fields['row_index'].choices), 8)
        self.assertContains(page, 'type="hidden" name="dataset"')
        self.assertNotContains(page, 'name="dataset" id="id_dataset"')
        again = self.client.post(reverse('planning:load-comparison-demos'))
        self.assertEqual(again.url, response.url)
        self.assertEqual(SourceBatch.objects.filter(status=State.DEMO).count(), 2)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, State.APPROVED)

    def test_district_role_loads_district_example_and_can_create_comparison(self):
        self.client.force_login(self.reviewer)
        loaded = self.client.post(reverse('planning:load-comparison-demos'))
        page = self.client.get(loaded.url)
        dataset = page.context['dataset']
        self.assertIn('District demonstration', dataset.title)
        target = page.context['form'].fields['indicator'].queryset.get(code='DEMO-11')
        self.assertTrue(all(item.is_mocked for item in page.context['form'].fields['indicator'].queryset))
        response = self.client.post(reverse('planning:assessment-create'), dict(
            dataset=dataset.pk, indicator=target.pk, row_index=7,
            mapping_notes='Matched invented annual crop definitions and example geography.', methodology_confirmed='on'))
        self.assertEqual(response.status_code, 302)
        record = Assessment.objects.latest('pk')
        self.assertEqual(record.status, State.DEMO)
        self.assertTrue(record.is_mocked)
        self.assertEqual(record.row_index, 7)
        self.assertContains(self.client.get(response.url), '660.00')

    def test_unapproved_sources_are_not_selectable_and_route_requires_post_and_role(self):
        self.batch.status = State.DRAFT
        self.batch.save()
        page = self.client.get(reverse('planning:assessment-create'), {'dataset': self.batch.pk})
        self.assertIsNone(page.context['dataset'])
        self.assertEqual(self.client.get(reverse('planning:load-comparison-demos')).status_code, 405)
        outsider = get_user_model().objects.create_user('dataset_outsider')
        self.client.force_login(outsider)
        self.assertEqual(self.client.post(reverse('planning:load-comparison-demos')).status_code, 403)
        self.assertEqual(SourceBatch.objects.filter(status=State.DEMO).count(), 0)

    def test_demo_identity_conflict_rolls_back_and_never_relabels_real_data(self):
        self.indicator.code = 'DEMO-RW'
        self.indicator.save()
        response = self.client.post(reverse('planning:load-comparison-demos'), follow=True)
        self.assertContains(response, 'conflict with existing records')
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.status, State.APPROVED)
        self.assertFalse(self.indicator.is_mocked)
        self.assertEqual(SourceBatch.objects.filter(is_mocked=True).count(), 0)

    def test_changing_selected_dataset_rebuilds_observation_choices(self):
        self.client.post(reverse('planning:load-comparison-demos'))
        demo = SourceBatch.objects.get(title='MOCKED · District demonstration')
        official = self.client.get(reverse('planning:assessment-create'), {'dataset': self.batch.pk})
        selected = self.client.get(reverse('planning:assessment-create'), {'dataset': demo.pk})
        self.assertEqual(official.context['form'].fields['row_index'].choices[-1][1].split(' · ')[-1], '170 MT')
        self.assertIn('660 MT', selected.context['form'].fields['row_index'].choices[-1][1])
        self.assertTrue(all(target.is_mocked for target in selected.context['form'].fields['indicator'].queryset))
