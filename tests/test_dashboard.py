"""Run the app from a public-files-only copy: ignored inputs cannot be required."""
from pathlib import Path
import shutil
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class PublicDashboardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='apasa-public-dashboard-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Deliberately copy only the exact public inputs. No data/ or local_data/.
        files = ['app.py', 'docs/day3_findings.md',
                 'outputs/day3/maize_overall_summary.csv']
        files += [str(p.relative_to(ROOT)) for p in (ROOT/'outputs/day3/figures').glob('*.png')]
        for relative in files:
            dest = self.root/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, dest)
        self.at = AppTest.from_file(str(self.root/'app.py'), default_timeout=20)

    def assert_clean(self):
        self.assertFalse(self.at.exception)
        self.assertFalse(self.at.error)

    def test_public_only_startup_chart_and_sample_denominators(self):
        self.at.run()
        self.assert_clean()
        self.assertFalse((self.root/'local_data').exists())
        self.assertFalse((self.root/'data').exists())
        self.assertEqual([m.value for m in self.at.metric[:4]], ['9,017','8,908','30 kg','92.12 kg'])
        self.assertEqual(len(self.at.get('vega_lite_chart') or self.at.get('arrow_vega_lite_chart')), 1)
        # The plotted chart is derived only from the two published seed report rows.
        seed = self.at.dataframe[1].value
        self.assertEqual(seed['Plot-season records'].tolist(), [3564,5311])
        self.assertEqual(seed['Observed harvest'].tolist(), [3555,5300])
        self.assertEqual(seed['Missing harvest'].tolist(), [9,11])
        self.assertEqual(seed['Observed median reported harvest (kg)'].tolist(), [15.,40.])
        status = self.at.dataframe[0].value
        self.assertEqual(status['Plot-season records'].tolist(), [8688,215,5,109])
        self.assertEqual(status['Plot-season records'].sum(),9017)
        self.assertIn('not national estimates', ' '.join(x.value for x in self.at.info))
        self.assertTrue(any('do not establish cause and effect' in info.value for info in self.at.info))

    def test_sensitivity_changes_only_overall_panel(self):
        self.at.run()
        self.at.radio[0].set_value('Exclude >5,000 kg · sensitivity only').run()
        self.assert_clean()
        self.assertEqual([m.value for m in self.at.metric[4:]], ['9,012','30 kg','86.91 kg'])
        self.assertEqual([m.value for m in self.at.metric[:4]], ['9,017','8,908','30 kg','92.12 kg'])
        seed = self.at.dataframe[1].value
        self.assertEqual(seed['Observed median reported harvest (kg)'].tolist(), [15.,40.])
        self.assertTrue(any('8,903 non-missing' in c.value for c in self.at.caption))
        self.at.radio[0].set_value('All records · main analysis').run()
        self.assertEqual([m.value for m in self.at.metric[4:]], ['9,017','30 kg','92.12 kg'])

    def test_all_eleven_published_chart_options(self):
        self.at.run()
        options = self.at.selectbox[0].options
        self.assertEqual(len(options),11)
        for option in options:
            with self.subTest(chart=option):
                self.at.selectbox[0].set_value(option).run()
                self.assert_clean()
                self.assertEqual(len(self.at.get('image') or self.at.get('imgs')),1)

    def test_unreconciled_public_summary_shows_error(self):
        path = self.root/'outputs/day3/maize_overall_summary.csv'
        path.write_text(path.read_text().replace('9017,9017,8908','9018,9017,8908'))
        self.at.run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.error),1)
        self.assertIn('denominators do not reconcile',self.at.error[0].value)
        self.assertEqual(len(self.at.metric),0)


if __name__ == '__main__':
    unittest.main()
