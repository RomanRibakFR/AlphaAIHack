(function(root){'use strict';
const finite=v=>typeof v==='number'&&Number.isFinite(v),obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const request=errors=>({status:'REQUEST_DATA',pd_probability:null,pd_percent:null,errors,contribution_details:[]});
function validateModel(m){
 if(!obj(m)||m.schema_version!=='synthetic-cashflow-pd-logit-v1')throw new Error('Unsupported model schema');
 const n=m.feature_order.length,p=m.preprocessing;
 if(m.coefficients.length!==n||!m.coefficients.every(finite))throw new Error('Invalid coefficients');
 for(const k of ['clip_enabled','clip_low','clip_high','transforms','mean','scale'])if(!Array.isArray(p[k])||p[k].length!==n)throw new Error('Invalid preprocessing '+k);
 if(p.impute_median!==undefined&&(!Array.isArray(p.impute_median)||p.impute_median.length!==n||!p.impute_median.every(v=>v===null||finite(v))))throw new Error('Invalid imputation metadata');
 if(!finite(m.intercept_final)||!p.scale.every(v=>finite(v)&&v>0))throw new Error('Invalid intercept/scales');return m;
}
function scoreFeatures(features,model){
 let m;try{m=validateModel(model);}catch(e){return request(['Model error: '+e.message]);}
 if(!obj(features))return request(['Features must be an object']);
 const names=m.feature_order,errors=names.filter(f=>!finite(features[f])).map(f=>f+': finite number required');
 if(errors.length)return request(errors);if(features.business_age_years<0)errors.push('Business age must be nonnegative');
 for(const f of ['is_small_business','industry_manufacturing','industry_construction','industry_trade','expenses_missing','simplified_reporting'])if(names.includes(f)&&f!=='business_age_years'&&features[f]!==0&&features[f]!==1)errors.push(f+': expected0or1');
 if(names.filter(f=>f.startsWith('industry_')).reduce((s,f)=>s+features[f],0)>1)errors.push('Industry groups must be mutually exclusive');
 if(names.includes('current_ratio')&&features.current_ratio<0)errors.push('Current ratio must be nonnegative');
 if(names.includes('asset_turnover')&&features.asset_turnover<=0)errors.push('Asset turnover must be positive');
 if(names.includes('short_term_liabilities_assets')&&features.short_term_liabilities_assets<=0)errors.push('CL/assets must be positive');
 if(names.includes('expenses_revenue')&&features.expenses_revenue<0)errors.push('Expense ratio must be nonnegative');
 if(names.includes('receipts_growth')&&features.receipts_growth<=-1)errors.push('Growth must exceed−1');
 for(const f of ['receipts_cv','cash_buffer_months'])if(names.includes(f)&&features[f]<0)errors.push(f+': expected nonnegative');
 if(names.includes('largest_customer_share')&&(features.largest_customer_share<0||features.largest_customer_share>1))errors.push('Share must be0..1');
 if(names.includes('cash_operating_margin')&&features.cash_operating_margin>1)errors.push('Cash margin cannot exceed1');
 if(errors.length)return request(errors);
 let z=m.intercept_final;const p=m.preprocessing,details=[],warnings=[];
 try{names.forEach((f,j)=>{const x=features[f],v=p.clip_enabled[j]?Math.min(p.clip_high[j],Math.max(p.clip_low[j],x)):x;
  if(v!==x)warnings.push({feature:f,original:x,clipped:v});
  const t=p.transforms[j]==='asinh'?Math.asinh(v):p.transforms[j]==='log1p'?Math.log1p(v):v,s=(t-p.mean[j])/p.scale[j],contribution=m.coefficients[j]*s;
  if(![t,s,contribution].every(finite))throw new Error('Nonfinite calculation');z+=contribution;
  details.push({feature:f,label:m.feature_labels[f]||f,input:x,clipped:v,transformed:t,standardized:s,coefficient:m.coefficients[j],logit_contribution:contribution});});
  if(!finite(z))throw new Error('Nonfinite logit');
 }catch(e){return request([e.message]);}
 const e=Math.exp(z>=0?-z:z),prob=z>=0?1/(1+e):e/(1+e);
 return{status:'SYNTHETIC_SIMULATOR',segment:m.segment,model_id:m.model_id,horizon_months:12,label:m.operational_target,pd_probability:prob,pd_percent:100*prob,intercept_final:m.intercept_final,logit:z,contribution_details:details,clipping_warnings:warnings,errors:[],calibration_status:m.calibration_status,quality_flags:m.quality_flags,synthetic_warning:"SYNTHETIC_SIMULATOR: probability and quality metrics describe an invented cashflow/repayment world. They do not establish real Russian IP/UL credit PD or model quality.",raw_features:Object.fromEntries(names.map(f=>[f,features[f]]))};
}
function deriveFeatures(inputs,m){
 if(!obj(inputs))throw new Error('Inputs must be an object');const age=inputs.business_age_years;
 if(!finite(age)||age<0)throw new Error('business_age_years: finite nonnegative number required');
 if(!['micro','small'].includes(inputs.msp_category))throw new Error("msp_category: choose'micro'or'small'");
 const f={business_age_years:age,is_small_business:Number(inputs.msp_category==='small')};
 if(m.common_features.some(x=>x.startsWith('industry_'))){
  if(typeof inputs.okved_main!=='string')throw new Error('okved_main: OKVED2code required, e.g.47.11');const code=inputs.okved_main.trim();
  if(!/^\d{2}(?:\.\d{1,2}){0,2}$/.test(code))throw new Error('okved_main: OKVED2code required, e.g.47.11');
  const sector=Number(code.slice(0,2));if(![1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 53, 55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99].includes(sector))throw new Error('Invalid OKVED2 division');
  Object.assign(f,{industry_manufacturing:Number(sector>=10&&sector<=33),industry_construction:Number(sector>=41&&sector<=43),industry_trade:Number(sector>=45&&sector<=47)});
 }

 const cashNames=['monthly_receipts_rub','monthly_operating_outflows_rub','existing_monthly_debt_service_rub','new_monthly_debt_service_rub','receipts_growth_6m_pct','receipts_cv_pct','cash_reserve_rub','largest_customer_share_pct'];
 if(!cashNames.every(k=>finite(inputs[k])))throw new Error('All eight cashflow inputs must be finite numbers in RUB/percent');
 const receipts=inputs.monthly_receipts_rub,outflows=inputs.monthly_operating_outflows_rub,existing=inputs.existing_monthly_debt_service_rub,newPayment=inputs.new_monthly_debt_service_rub,reserve=inputs.cash_reserve_rub,growth=inputs.receipts_growth_6m_pct,cv=inputs.receipts_cv_pct,share=inputs.largest_customer_share_pct;
 if(receipts<=0||outflows<0||existing<0||newPayment<=0||reserve<0||growth<=-100||cv<0||share<0||share>100)throw new Error('Cash domains: receipts/new payment>0; outflows/existing payment/reserve/CV>=0; growth>−100%; largest share0..100%');
 const service=existing+newPayment;if(!finite(service)||!finite(outflows+service))throw new Error('Cashflow sums exceed numeric range');Object.assign(f,{debt_coverage:(receipts-outflows)/service,receipts_growth:growth/100,receipts_cv:cv/100,cash_buffer_months:reserve/(outflows+service),largest_customer_share:share/100,cash_operating_margin:(receipts-outflows)/receipts});
 if(m.segment==='ul'){
  if(!['rub','thousand_rub'].includes(inputs.unit))throw new Error('Choose unit rub or thousand_rub');
  if(!['assets','equity','current_assets','current_liabilities','revenue','net_profit'].every(k=>finite(inputs[k])))throw new Error('All six financial amounts must be finite numbers');
  const a=inputs.assets,cl=inputs.current_liabilities,r=inputs.revenue,ca=inputs.current_assets;
  if(a<=0||cl<=0||r<=0||ca<0)throw new Error('Assets/revenue/currentliabilities must be positive; currentassets nonnegative');
  if(ca>a+(inputs.unit==='rub'?3000:3))throw new Error('Current assets exceed assets beyond tolerance');
  Object.assign(f,{equity_assets:inputs.equity/a,current_ratio:ca/cl,net_margin:inputs.net_profit/r,asset_turnover:r/a});
  if(m.feature_order.includes('short_term_liabilities_assets'))f.short_term_liabilities_assets=cl/a;
  if(m.feature_order.includes('simplified_reporting')){if(!['full','simplified'].includes(inputs.report_form))throw new Error('report_form: choose full or simplified');f.simplified_reporting=Number(inputs.report_form==='simplified');}
  if(m.feature_order.includes('expenses_revenue')){
   const expense=inputs.ordinary_expenses;
   if(expense===null||expense===undefined){const j=m.feature_order.indexOf('expenses_revenue'),median=(m.preprocessing.impute_median||[])[j];if(!finite(median))throw new Error('Missing fitted TRAIN median for expenses_revenue');Object.assign(f,{expenses_revenue:median,expenses_missing:1});}
   else{if(!finite(expense)||expense<0)throw new Error('ordinary_expenses: nonnegative amount or null required');Object.assign(f,{expenses_revenue:expense/r,expenses_missing:0});}
  }
 }
 return f;
}
function score(inputs,model){try{validateModel(model);const f=deriveFeatures(inputs,model),r=scoreFeatures(f,model);r.imputed_features=f.expenses_missing===1?['expenses_revenue']:[];r.imputation_warnings=r.imputed_features.length?['Expense ratio replaced by observed TRAIN median; expenses_missing=1. Zero is an observed amount.']:[];return r;}catch(e){return request([e.message]);}}
const api={score,scoreFeatures,deriveFeatures,validateModel};root.ULSyntheticPD=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
