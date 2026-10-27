"""Boundary tests for transformations and statistical comparison safeguards."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare import deaccumulate,hard_invalid
from features import mean_roll,build_features
from ranking import tail_proportion,equal_year_weights,max_and_representative
from common import CATALOG,anchors

class AnalysisRules(unittest.TestCase):
    def test_catalog_complete(self):
        self.assertEqual(len(CATALOG),31);self.assertEqual(CATALOG.indicator.nunique(),14)
        self.assertEqual(CATALOG.group.nunique(),10)
        self.assertEqual(CATALOG.location.value_counts().to_dict(),{'station':18,'source':13})
        self.assertFalse(CATALOG.feature.str.contains('QC').any())

    def test_midnight_reset(self):
        s=pd.Series([2300.,2400.,100.,200.],index=pd.date_range('2026-08-25 23:00',periods=4,freq='h'))
        np.testing.assert_allclose(deaccumulate(s).values,[np.nan,100,100,100],equal_nan=True)

    def test_month_gap_not_differenced(self):
        idx=pd.to_datetime(['2021-09-30 23:00','2022-07-01 00:00','2022-07-01 01:00'])
        s=pd.Series([100,200,5.],index=idx)
        self.assertTrue(np.isnan(deaccumulate(s).iloc[1]));self.assertEqual(deaccumulate(s).iloc[2],5)

    def test_missing_cumulative_propagates(self):
        s=pd.Series([1,np.nan,4,6],index=pd.date_range('2026-08-25 01:00',periods=4,freq='h'))
        out=deaccumulate(s)
        self.assertTrue(np.isnan(out.iloc[1]));self.assertTrue(np.isnan(out.iloc[2]));self.assertEqual(out.iloc[3],2)

    def test_true_zero_preserved(self):
        s=pd.Series([0.,1.,-1.]);self.assertEqual(hard_invalid(s,'Precip(mm)').tolist(),[False,False,True])

    def test_signed_heat_preserved(self):
        s=pd.Series([-200.,0.,200.]);self.assertFalse(hard_invalid(s,'H(W/m2)').any())

    def test_mean_coverage(self):
        s=pd.Series(np.arange(24,dtype=float));s.iloc[[1,2]]=np.nan
        mean,n=mean_roll(s,24,.9);self.assertTrue(np.isfinite(mean.iloc[-1]));self.assertEqual(n.iloc[-1],22)
        s.iloc[3]=np.nan;self.assertTrue(np.isnan(mean_roll(s,24,.9)[0].iloc[-1]))

    def test_empty_block_rejected(self):
        s=pd.Series(np.ones(24));s.iloc[6:12]=np.nan
        self.assertTrue(np.isnan(mean_roll(s,24,.7)[0].iloc[-1]))

    def test_zero_tie_is_not_extreme(self):
        r=pd.Series(np.zeros(20),index=pd.date_range('2021-08-01',periods=20))
        self.assertEqual(tail_proportion(r,[0],'upper')[0],1)
        self.assertEqual(tail_proportion(r,[0],'two')[0],1)

    def test_equal_year_weight(self):
        index=pd.to_datetime(['2021-08-01','2021-08-02','2022-08-01'])
        w=equal_year_weights(index);np.testing.assert_allclose(w,[.25,.25,.5])

    def test_extreme_has_finite_resolution(self):
        r=pd.Series(np.arange(20),index=pd.date_range('2021-08-01',periods=20))
        self.assertAlmostEqual(tail_proportion(r,[100],'upper')[0],1/21)

    def test_missing_group_column_does_not_reduce_search(self):
        d=pd.DataFrame({'a':[2.,np.nan],'b':[1.,5.]})
        maxima,rep=max_and_representative(d)
        self.assertTrue(np.isnan(maxima.iloc[1]));self.assertEqual(rep.iloc[1],'')

    def test_calendar_anchors(self):
        a=anchors();self.assertEqual(len(a),155)
        self.assertTrue(all((a.month>=8)&(a.month<=9)))
        self.assertEqual(a[a.year==2024].min().strftime('%m-%d'),'08-11')

    def test_future_does_not_affect_past_features(self):
        idx=pd.date_range('2026-08-01',periods=220,freq='h')
        columns=['T2','P','U10','RH2','Rn','LWnet','H','LE','VWC01','GT','TKE','USTAR']
        d=pd.DataFrame(1.,index=idx,columns=columns);cut=idx[190]
        a,_=build_features(d,d)
        altered=d.copy();altered.loc[altered.index>cut,:]=999
        b,_=build_features(altered,altered)
        np.testing.assert_allclose(a.loc[cut],b.loc[cut],equal_nan=True)

if __name__=='__main__':unittest.main()
