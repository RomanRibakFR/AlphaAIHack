"""SYNTHETIC_SIMULATOR: standard-library inference for fictional cashflow/90DPD. Not real credit PD."""
from pathlib import Path
import argparse,json,math,re

def load_model(path=None):
    return json.loads(Path(path or Path(__file__).with_name('model.json')).read_text(encoding='utf-8'))

def finite(v):
    try:return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)
    except (OverflowError,TypeError):return False
def request(errors):return {'status':'REQUEST_DATA','pd_probability':None,'pd_percent':None,'errors':errors,'contribution_details':[]}

def validate_model(m):
    if not isinstance(m,dict) or m.get('schema_version')!='synthetic-cashflow-pd-logit-v1':raise ValueError('Unsupported model schema')
    f=m['feature_order'];p=m['preprocessing'];n=len(f)
    if len(m['coefficients'])!=n or not all(finite(v) for v in m['coefficients']):raise ValueError('Invalid coefficients')
    for k in ['clip_enabled','clip_low','clip_high','transforms','mean','scale']:
        if not isinstance(p[k],list) or len(p[k])!=n:raise ValueError('Invalid preprocessing '+k)
    if 'impute_median' in p and (len(p['impute_median'])!=n or not all(v is None or finite(v) for v in p['impute_median'])):raise ValueError('Invalid imputation metadata')
    if not finite(m['intercept_final']) or not all(finite(v) and v>0 for v in p['scale']):raise ValueError('Invalid intercept/scales')
    return m

def score_features(features,model=None):
    try:m=validate_model(model or load_model())
    except (ValueError,KeyError,TypeError,OSError) as e:return request(['Model error: '+str(e)])
    if not isinstance(features,dict):return request(['Features must be an object'])
    names=m['feature_order'];errors=[f+': finite number required' for f in names if not finite(features.get(f))]
    if errors:return request(errors)
    if features['business_age_years']<0:errors.append('Business age must be nonnegative')
    for f in ['is_small_business','industry_manufacturing','industry_construction','industry_trade','expenses_missing','simplified_reporting']:
        if f in names and f!='business_age_years' and features[f] not in [0,1]:errors.append(f+': expected0or1')
    industry=[f for f in names if f.startswith('industry_')]
    if sum(features[f] for f in industry)>1:errors.append('Industry groups must be mutually exclusive')
    if 'current_ratio' in names and features['current_ratio']<0:errors.append('Current ratio must be nonnegative')
    if 'asset_turnover' in names and features['asset_turnover']<=0:errors.append('Asset turnover must be positive')
    if 'short_term_liabilities_assets' in names and features['short_term_liabilities_assets']<=0:errors.append('CL/assets must be positive')
    if 'expenses_revenue' in names and features['expenses_revenue']<0:errors.append('Expense ratio must be nonnegative')
    if 'receipts_growth' in names and features['receipts_growth']<=-1:errors.append('Growth must exceed−1')
    for f in ['receipts_cv','cash_buffer_months']:
        if f in names and features[f]<0:errors.append(f+': expected nonnegative')
    if 'largest_customer_share' in names and not 0<=features['largest_customer_share']<=1:errors.append('Share must be0..1')
    if 'cash_operating_margin' in names and features['cash_operating_margin']>1:errors.append('Cash margin cannot exceed1')
    if errors:return request(errors)
    p=m['preprocessing'];details=[];warnings=[];z=m['intercept_final']
    try:
        for j,f in enumerate(names):
            x=float(features[f]);v=min(p['clip_high'][j],max(p['clip_low'][j],x)) if p['clip_enabled'][j] else x
            if v!=x:warnings.append({'feature':f,'original':x,'clipped':v})
            t=math.asinh(v) if p['transforms'][j]=='asinh' else math.log1p(v) if p['transforms'][j]=='log1p' else v
            standardized=(t-p['mean'][j])/p['scale'][j];contribution=m['coefficients'][j]*standardized
            if not all(math.isfinite(a) for a in [t,standardized,contribution]):raise ValueError('Nonfinite calculation')
            z+=contribution;details.append({'feature':f,'label':m['feature_labels'].get(f,f),'input':x,'clipped':v,'transformed':t,'standardized':standardized,'coefficient':m['coefficients'][j],'logit_contribution':contribution})
        if not math.isfinite(z):raise ValueError('Nonfinite logit')
        prob=1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
    except (ValueError,OverflowError,ZeroDivisionError) as e:return request([str(e)])
    return {'status':'SYNTHETIC_SIMULATOR','segment':m['segment'],'model_id':m['model_id'],'horizon_months':12,'label':m['operational_target'],'pd_probability':prob,'pd_percent':100*prob,'intercept_final':m['intercept_final'],'logit':z,'contribution_details':details,'clipping_warnings':warnings,'errors':[],'calibration_status':m['calibration_status'],'quality_flags':m['quality_flags'],'synthetic_warning':'SYNTHETIC_SIMULATOR: probability and quality metrics describe an invented cashflow/repayment world. They do not establish real Russian IP/UL credit PD or model quality.','raw_features':{f:float(features[f]) for f in names}}

def derive_features(inputs,model):
    if not isinstance(inputs,dict):raise ValueError('Inputs must be an object')
    age=inputs.get('business_age_years')
    if not finite(age) or age<0:raise ValueError('business_age_years: finite nonnegative number required')
    category=inputs.get('msp_category')
    if category not in ['micro','small']:raise ValueError("msp_category: choose'micro'or'small'")
    features={'business_age_years':float(age),'is_small_business':int(category=='small')}
    if any(f.startswith('industry_') for f in model['common_features']):
        code=inputs.get('okved_main')
        if not isinstance(code,str):raise ValueError('okved_main: OKVED2code required, e.g.47.11')
        code=code.strip()
        if not re.fullmatch(r'\d{2}(?:\.\d{1,2}){0,2}',code):raise ValueError('okved_main: OKVED2code required, e.g.47.11')
        sector=int(code[:2])
        if sector not in [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 53, 55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99]:raise ValueError('Invalid OKVED2 division')
        features.update(industry_manufacturing=int(10<=sector<=33),industry_construction=int(41<=sector<=43),industry_trade=int(45<=sector<=47))

    cash_names=['monthly_receipts_rub','monthly_operating_outflows_rub','existing_monthly_debt_service_rub','new_monthly_debt_service_rub','receipts_growth_6m_pct','receipts_cv_pct','cash_reserve_rub','largest_customer_share_pct']
    if not all(finite(inputs.get(f)) for f in cash_names):raise ValueError('All eight cashflow inputs must be finite numbers in RUB/percent')
    receipts=inputs['monthly_receipts_rub'];outflows=inputs['monthly_operating_outflows_rub'];existing=inputs['existing_monthly_debt_service_rub'];new=inputs['new_monthly_debt_service_rub'];reserve=inputs['cash_reserve_rub'];growth=inputs['receipts_growth_6m_pct'];cv=inputs['receipts_cv_pct'];share=inputs['largest_customer_share_pct']
    if receipts<=0 or outflows<0 or existing<0 or new<=0 or reserve<0 or growth<=-100 or cv<0 or not 0<=share<=100:raise ValueError('Cash domains: receipts/new payment>0; outflows/existing payment/reserve/CV>=0; growth>−100%; largest share0..100%')
    service=existing+new
    if not math.isfinite(service) or not math.isfinite(outflows+service):raise ValueError('Cashflow sums exceed numeric range')
    features.update(debt_coverage=(receipts-outflows)/service,receipts_growth=growth/100,receipts_cv=cv/100,cash_buffer_months=reserve/(outflows+service),largest_customer_share=share/100,cash_operating_margin=(receipts-outflows)/receipts)
    if model['segment']=='ul':
        if inputs.get('unit') not in ['rub','thousand_rub']:raise ValueError('Choose unit rub or thousand_rub')
        names=['assets','equity','current_assets','current_liabilities','revenue','net_profit']
        if not all(finite(inputs.get(f)) for f in names):raise ValueError('All six financial amounts must be finite numbers')
        a=inputs['assets'];cl=inputs['current_liabilities'];revenue=inputs['revenue'];ca=inputs['current_assets']
        if a<=0 or cl<=0 or revenue<=0 or ca<0:raise ValueError('Assets/revenue/currentliabilities must be positive; currentassets nonnegative')
        if ca>a+(3000 if inputs['unit']=='rub' else 3):raise ValueError('Current assets exceed assets beyond tolerance')
        features.update(equity_assets=inputs['equity']/a,current_ratio=ca/cl,net_margin=inputs['net_profit']/revenue,asset_turnover=revenue/a)
        if 'short_term_liabilities_assets' in model['feature_order']:features['short_term_liabilities_assets']=cl/a
        if 'simplified_reporting' in model['feature_order']:
            form=inputs.get('report_form')
            if form not in ['full','simplified']:raise ValueError('report_form: choose full or simplified')
            features['simplified_reporting']=int(form=='simplified')
        if 'expenses_revenue' in model['feature_order']:
            expense=inputs.get('ordinary_expenses')
            if expense is None:
                j=model['feature_order'].index('expenses_revenue');median=model['preprocessing'].get('impute_median',[None]*len(model['feature_order']))[j]
                if not finite(median):raise ValueError('Missing fitted TRAIN median for expenses_revenue')
                features.update(expenses_revenue=float(median),expenses_missing=1)
            else:
                if not finite(expense) or expense<0:raise ValueError('ordinary_expenses: nonnegative amount or null required')
                features.update(expenses_revenue=expense/revenue,expenses_missing=0)
    return features

def score(inputs,model=None):
    try:m=validate_model(model or load_model());features=derive_features(inputs,m)
    except (ValueError,KeyError,TypeError,OSError,ZeroDivisionError,OverflowError) as e:return request([str(e)])
    result=score_features(features,m)
    result['imputed_features']=['expenses_revenue'] if features.get('expenses_missing')==1 else []
    result['imputation_warnings']=['Expense ratio replaced by observed TRAIN median; expenses_missing=1. Zero is an observed amount.'] if result['imputed_features'] else []
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--model',type=Path);args=p.parse_args()
    result=score(json.loads(args.input.read_text(encoding='utf-8')),load_model(args.model));print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
if __name__=='__main__':main()
