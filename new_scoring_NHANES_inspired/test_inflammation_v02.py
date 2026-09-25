"""Independent composite contract checks; not clinical validation."""
from copy import deepcopy
import unittest
from test_inflammation_score import profile, score


class CompositeTests(unittest.TestCase):
    def test_worked_total_and_flags(self):
        r=score(profile())
        self.assertAlmostEqual(r['domain_score'],82.1818181818)
        self.assertEqual(r['display_score'],'82.2')
        self.assertEqual(r['score'],r['domain_score'])
        self.assertTrue(r['review_required'])
        p=profile(.5)
        self.assertAlmostEqual(score(p)['domain_score'],98.1818181818)
        self.assertTrue(score(p)['review_required'])

    def test_wbc_both_tails_and_units(self):
        for x,expected in [(0,0),(2,50),(4,100),(8,100),(11,100),(16.5,50),(22,0),(100,0)]:
            for unit,factor in [('10^9/L',1),('cells/uL',1000),('10^3/uL',1)]:
                p=profile()
                p['observations']['wbc'].update(value=x*factor,unit=unit,lower_limit=4*factor,upper_limit=11*factor)
                r=score(p)
                self.assertAlmostEqual(r['marker_scores']['wbc'],expected)
                self.assertAlmostEqual(r['domain_score'],64+.2*expected)

    def test_missing_core_never_reweights(self):
        for marker in ('hs_crp','wbc'):
            p=profile(); del p['observations'][marker]
            r=score(p)
            self.assertIsNone(r['domain_score'])
            self.assertIn(marker,r['coverage']['missing_or_unusable'])
            self.assertEqual(len(r['coverage']['scored']),1)

    def test_wbc_metadata_and_bounds(self):
        for update in [{'reference_range_applicable':False},{'lower_limit':0},{'upper_limit':3},
                       {'qualifier':'<'},{'unit':'%'},{'reliability':'unreliable'},
                       {'specimen_date':None},{'report_id':''},{'value':-1},{'reference_unit':'wrong'}]:
            p=profile();p['observations']['wbc'].update(update)
            self.assertIsNone(score(p)['domain_score'],update)
            self.assertEqual(score(p)['marker_scores']['hs_crp'],80)

    def test_dates_must_match_even_when_individual_points_exist(self):
        p=profile();p['observations']['wbc']['specimen_date']='2026-09-02'
        r=score(p)
        self.assertIsNone(r['domain_score'])
        self.assertEqual(len(r['coverage']['scored']),2)
        self.assertIn('core_collection_dates_must_match',r['reasons'])

    def test_selection_and_duplicate_ids(self):
        p=profile();w=p['observations']['wbc'];w['observation_id']='w1'
        second=deepcopy(w);second.update(observation_id='w2',value=8)
        p['observations']['wbc']=[w,second]
        self.assertIsNone(score(p)['domain_score'])
        p['selected_wbc_id']='w2'
        self.assertEqual(score(p)['domain_score'],84)
        p['selected_wbc_id']='missing'
        self.assertIsNone(score(p)['domain_score'])
        second['observation_id']='synthetic-hscrp'
        self.assertIsNone(score(p)['domain_score'])

    def test_context_is_not_counted_twice(self):
        p=profile();before=score(p)['domain_score']
        p['observations']['absolute_neutrophils']={'value':90,'unit':'%','lab_flag':'Critical'}
        self.assertEqual(score(p)['domain_score'],before)
        self.assertTrue(score(p)['review_required'])

    def test_baseline_eligibility_applies_to_both_markers(self):
        for state in ('present','unknown'):
            p=profile();p['context']['acute_context']=state
            self.assertIsNone(score(p)['domain_score'])
            self.assertIsNone(score(p)['components']['wbc']['score'])
        p=profile();p['person']['pregnancy_status']='pregnant'
        self.assertIsNone(score(p)['components']['wbc']['score'])

