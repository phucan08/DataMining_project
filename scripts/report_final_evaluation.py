"""Create final holdout figures and reports solely from saved evaluation outputs."""
from __future__ import annotations
import json,sys
from pathlib import Path
import pandas as pd
from reportlab.graphics.shapes import Line,Rect,String
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.final_evaluation import digest,verify_records
from src.plotting import figure,note,save,PALETTE

LABELS={'popularity':'Popularity','global_rules':'Global rules (all train)',
        'global_identified_rules':'Global rules (identified train)','segment_rules':'Segment rules'}


def main():
    from report_documentation import retain_frozen_english_reports
    if retain_frozen_english_reports(ROOT,['docs/final_evaluation_report.md','report/project_report.md']):
        return
    base=ROOT/'results/tables/final_test'
    receipt=json.loads((base/'evaluation_receipt.json').read_text())
    lock=ROOT/'results/models/final_evaluation_lock.json'
    assert digest(lock)==receipt['freeze_lock_sha256']
    verify_records(ROOT,json.loads(lock.read_text())['files']);verify_records(ROOT,receipt['files'])
    metrics=pd.read_csv(base/'completion_metrics.csv')
    intervals=pd.read_csv(base/'bootstrap_intervals.csv')
    contrasts=pd.read_csv(base/'paired_bootstrap_contrasts.csv')
    cohorts=pd.read_csv(base/'cohort_audit.csv')
    stability=pd.read_csv(base/'rule_stability_summary.csv')
    profile=pd.read_csv(ROOT/'results/tables/models/cluster_profiles.csv')
    selected=pd.read_csv(ROOT/'results/tables/models/selected_global_rules.csv',dtype={'antecedent':'string','consequent':'string'})
    test_rules=pd.read_csv(base/'selected_global_rule_stability.csv',dtype={'antecedent':'string','consequent':'string'})
    rules=selected.merge(test_rules[['antecedent','consequent','test_count_ab','test_confidence','test_lift']],on=['antecedent','consequent'],validate='one_to_one')
    d=figure('Final test: frozen rules and customer segments',
             '2011-10-01 to 2011-12-09. One hidden product per invoice; no model refitting.',width=1200,height=650)
    for panel,(cohort,names,title) in enumerate([
        ('all_baskets',['popularity','global_rules'],'All eligible baskets (N=5,183)'),
        ('train_profile_customers',['popularity','global_identified_rules','segment_rules'],'Same train-profile cohort (N=3,579)')]):
        x0=85+panel*600;y0=180;width=490;height=310;maximum=12
        for tick in [0,3,6,9,12]:
            y=y0+height*tick/maximum
            d.add(Line(x0,y,x0+width,y,strokeColor=colors.HexColor('#e2e8f0')))
            d.add(String(x0-12,y-3,str(tick),textAnchor='end',fontSize=10))
        d.add(String(x0,y0+height+35,title,fontName='Helvetica-Bold',fontSize=13))
        d.add(String(x0,y0+height+15,'HitRate@5 (%) with 95% customer-cluster bootstrap intervals',fontSize=9))
        for i,name in enumerate(names):
            row=intervals.loc[intervals['cohort'].eq(cohort)&intervals['method'].eq(name)].iloc[0]
            x=x0+width*(i+.5)/len(names);barwidth=75
            value=100*row['estimate']; y=y0+height*value/maximum
            d.add(Rect(x-barwidth/2,y0,barwidth,y-y0,fillColor=colors.HexColor(PALETTE[i]),strokeColor=None))
            lo=y0+height*(100*row['ci95_lower'])/maximum;hi=y0+height*(100*row['ci95_upper'])/maximum
            d.add(Line(x,lo,x,hi,strokeColor=colors.black,strokeWidth=1.3))
            for bound in [lo,hi]:d.add(Line(x-8,bound,x+8,bound,strokeColor=colors.black))
            d.add(String(x,hi+10,f'{value:.2f}%',textAnchor='middle',fontName='Helvetica-Bold',fontSize=12))
            label={'global_rules':'Global rules','global_identified_rules':'Global (identified)','segment_rules':'Segment rules','popularity':'Popularity'}[name]
            d.add(String(x,y0-22,label,textAnchor='middle',fontSize=10))
    note(d,'Paired 2,000-resample bootstrap. Segment-global difference interval includes zero. Guest invoices are separate bootstrap units.')
    save(d,ROOT/'results/figures/16_final_test_comparison.svg')

    def table(cohort):
        out=['| Phương án | Hits / giỏ | HitRate@5 | CI 95% | Precision@5 | Rule coverage |',
             '|---|---:|---:|---:|---:|---:|']
        for row in metrics.loc[metrics['cohort'].eq(cohort)].itertuples():
            ci=intervals.loc[intervals['cohort'].eq(cohort)&intervals['method'].eq(row.method)].iloc[0]
            out.append(f'| {LABELS[row.method]} | {row.hits}/{row.eligible_baskets} | {row.hit_rate_at_5:.2%} | [{ci.ci95_lower:.2%}; {ci.ci95_upper:.2%}] | {row.precision_at_5_fixed_denominator:.2%} | {row.rule_coverage:.2%} |')
        return out

    lines=['# Đánh giá final test với mô hình đã khóa','',
           '## 1. Cấu hình và nguyên tắc đánh giá','',
           'Final test gồm các hóa đơn từ 01/10/2011 đến hết 09/12/2011. Giữ nguyên 738 luật global, 455 luật global trên cohort định danh, 574/230 luật của hai segment và K-means K=2 đã học từ train. Không refit bằng validation hoặc test, không đổi support/confidence/K sau khi xem test.',
           '', 'Protocol bổ sung được lưu trước khi chấm test tại configs/final_evaluation_protocol.json. Mã băm của dữ liệu, luật, model, scaler và mã đánh giá được khóa tại results/models/final_evaluation_lock.json. Receipt lưu thời điểm thực hiện và hash mọi đầu ra. Lần gọi sau chỉ kiểm tra kết quả đã lưu.',
           '', 'Ẩn một sản phẩm trong giỏ có ít nhất hai sản phẩm khác nhau bằng đúng hash invoice/seed 42 đã dùng ở validation. Giữ sản phẩm đích chưa xuất hiện trong train trong mẫu số; candidate và xếp hạng chỉ từ train. Loại sản phẩm đã nhìn thấy khỏi gợi ý, điền đủ tối đa 5 sản phẩm bằng popularity train.',
           '', 'Trong so sánh toàn bộ giỏ, global và baseline dùng popularity toàn train. Trong so sánh segment, cả ba phương án dùng cùng cohort khách có hồ sơ train và popularity trên train định danh. Do đó không so trực tiếp hai hàng có cùng tên nhưng khác cohort/nguồn huấn luyện.',
           '', '## 2. Cohort và sản phẩm mới','',
           '| Cohort | Tổng giỏ | Đủ điều kiện | Giỏ một sản phẩm | Khách có ID | Target chưa thấy trong train |',
           '|---|---:|---:|---:|---:|---:|']
    for row in cohorts.itertuples():lines.append(f'| {row.cohort} | {row.total_baskets:,} | {row.eligible_baskets:,} | {row.single_item_baskets:,} | {row.identified_customers:,} | {row.targets_unseen_in_train:,} |')
    lines += ['', 'Có 389 giỏ một sản phẩm nằm ngoài bài toán ẩn item nhưng vẫn được giữ trong mẫu số khi tính support của luật trên test. Khách mới/thiếu ID không được gán cụm giả. Số khách trong bảng cohort là mọi khách của cohort; bootstrap chỉ gồm các khách có giỏ đủ điều kiện.',
              '', '## 3. Kết quả toàn bộ giỏ','',*table('all_baskets'),'',
              'Global trúng 458/5.183 giỏ, popularity trúng 90/5.183. Chênh lệch **+7,10 điểm phần trăm**, khoảng tin cậy bootstrap 95% **[+6,34; +7,89] điểm phần trăm**. Đây là bằng chứng trong bài toán hoàn thiện giỏ ngoại tuyến ở giai đoạn này, không phải mức tăng doanh thu hoặc hiệu quả triển khai thực tế.',
              '', '## 4. Global và segment trên cùng cohort','',*table('train_profile_customers'),'',
              'Segment trúng nhiều hơn global định danh đúng 2 giỏ: 317 so với 315 trên 3.579 giỏ. Chênh lệch **+0,056 điểm phần trăm**, CI 95% **[−0,475; +0,600] điểm phần trăm**. Khoảng chứa 0 nên chưa đủ bằng chứng nói segment rules tốt hơn; cũng không chứng minh hai phương án tương đương.',
              '', '![Final test và khoảng tin cậy](../results/figures/16_final_test_comparison.png)','',
              '## 5. Định nghĩa metric và độ bất định','',
              '- HitRate@5: số giỏ chứa target trong top 5 chia số giỏ đủ điều kiện. Một target/giỏ nên Recall@5 có cùng giá trị.',
              '- Precision@5 dùng mẫu số cố định 5: tổng hit/(5 × số giỏ). Nếu trả thiếu 5, vị trí còn thiếu vẫn tính vào mẫu số. Lần chạy này mọi phương án đều trả đủ 5.',
              '- Rule coverage là tỷ lệ giỏ có ít nhất một gợi ý từ luật. Zero-rule fallback là phần bù của coverage; giỏ có luật vẫn có thể cần popularity để điền các vị trí còn thiếu.',
              '- Bootstrap paired 2.000 lần, seed 20261118, resample CustomerID rồi giữ toàn bộ giỏ của khách. Cùng mẫu resample cho các phương án; tỷ lệ vẫn là trung bình theo giỏ. Hóa đơn thiếu ID được coi là từng đơn vị riêng.',
              '- CI là percentile 2,5%–97,5%, điều kiện trên model/giai đoạn đã cố định; không bao gồm bất định do huấn luyện lại, không điều chỉnh nhiều phép so sánh, không thay cho A/B test. Giả định độc lập giữa các hóa đơn thiếu ID có thể chưa đúng.',
              '', '## 6. Kết quả theo nhóm khách và phân khúc','',
              '| Cohort | Phương án | Giỏ đủ điều kiện | HitRate@5 | Rule coverage |',
              '|---|---|---:|---:|---:|']
    for row in metrics.loc[~metrics['cohort'].isin(['all_baskets','train_profile_customers'])].itertuples():
        lines.append(f'| {row.cohort} | {LABELS[row.method]} | {row.eligible_baskets:,} | {row.hit_rate_at_5:.2%} | {row.rule_coverage:.2%} |')
    lines += ['', 'Các phân tích theo segment là mô tả, chưa có CI riêng/điều chỉnh nhiều so sánh. Không dùng kết quả này để chọn lại K hoặc đổi phương án cho từng segment trên chính test.',
              '', '## 7. Độ ổn định của luật cố định','',
              '| Nhóm | Luật cố định | Giỏ test tính support | Antecedent không xuất hiện | Joint count <20 | Joint count ≥20 | Lift test >1 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for row in stability.itertuples():lines.append(f'| {row.group} | {row.fixed_rules} | {row.test_baskets} | {row.test_antecedent_absent} | {row.test_joint_count_below_20} | {row.test_joint_count_at_least_20} | {row.test_lift_above_1} |')
    lines += ['', 'Mốc 20 ở đây chỉ là cờ mô tả lượng bằng chứng, không phải phép kiểm định. Confidence/lift không xác định được để trống khi mẫu số bằng 0. Không lọc lại luật bằng test rồi chấm lại.',
              '', '## 8. Vì sao cần phân biệt validation và test','',
              'Global HitRate@5 giảm từ 13,76% validation xuống 8,84% test. Tỷ lệ target chưa xuất hiện train tăng từ 188/2.944 = 6,39% lên 743/5.183 = 14,33%. Mô hình chỉ có candidate train nên không thể trúng các target mới này. Thay đổi cơ cấu sản phẩm/thời gian và sai lệch do chọn cấu hình trên validation là các khả năng giải thích, chưa phải kết luận nguyên nhân.',
              '', 'Các ví dụ lỗi được lấy theo thứ tự InvoiceNo, không lựa chọn theo câu chuyện thuận lợi. Xem [error_examples.csv](../results/tables/final_test/error_examples.csv). Chưa thực hiện tái huấn luyện theo tháng; đó là nghiên cứu sau, cần giai đoạn đánh giá mới.',
              '', '## 9. Kiểm chứng và đường dẫn đầu ra','',
              '- 24 tests đạt, gồm kiểm tra khóa hash, cohort paired, bootstrap theo khách, target mới và mẫu số Precision@5.',
              '- [completion_metrics.csv](../results/tables/final_test/completion_metrics.csv), [cohort_audit.csv](../results/tables/final_test/cohort_audit.csv), [bootstrap_intervals.csv](../results/tables/final_test/bootstrap_intervals.csv), [paired_bootstrap_contrasts.csv](../results/tables/final_test/paired_bootstrap_contrasts.csv).',
              '- [case_predictions.csv.gz](../results/tables/final_test/case_predictions.csv.gz) lưu từng target, gợi ý, hit và bootstrap unit để kiểm tra lại.',
              '- [evaluation_receipt.json](../results/tables/final_test/evaluation_receipt.json) và [final_evaluation_lock.json](../results/models/final_evaluation_lock.json) lưu bằng chứng khóa trước khi chấm điểm.',
              '- [Protocol](../configs/final_evaluation_protocol.json). Chạy `& .\\scripts\\run_final_evaluation.ps1` để kiểm chứng kết quả đã lưu và dựng lại báo cáo/hình; không chấm lại nếu đã có receipt.',
              '', 'Bước còn lại là đối chiếu rubric, hoàn thiện bản nộp/slide, tập trình bày và kiểm tra gói nộp. Test đã được sử dụng; mọi thay đổi mô hình tiếp theo phải ghi rõ và không coi lần đánh giá lại trên cùng test là độc lập.']
    (ROOT/'docs/final_evaluation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    main=['# Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation','',
          'Báo cáo nghiên cứu — bản nội dung hoàn chỉnh, cần bổ sung tên nhóm/thành viên và định dạng theo rubric trước khi nộp.','',
          '## Tóm tắt','',
          'Project phân tích UCI Online Retail bằng luật kết hợp và phân khúc khách hàng RFM. Sau kiểm tra chất lượng, có 522.537 dòng mua hàng hóa hợp lệ và 19.773 giỏ. Train trước 01/08/2011 được dùng để khai phá luật và tạo RFM cho 3.145 khách; validation tháng 8–9 chọn cấu hình; test tháng 10–09/12 đánh giá một lần với model đã khóa. Cấu hình được chọn gồm 738 luật và K-means K=2. Trên 5.183 giỏ test đủ điều kiện, luật global đạt HitRate@5 8,84%, baseline popularity 1,74%. So sánh trên cùng cohort 3.579 giỏ khách có hồ sơ train cho thấy luật segment 8,86% và global định danh 8,80%, chênh lệch chưa có bằng chứng rõ ràng theo CI bootstrap. Phân cụm hỗ trợ mô tả khách hàng nhưng chưa chứng minh cải thiện gợi ý.','',
          '## 1. Vấn đề và câu hỏi nghiên cứu','',
          'Mục tiêu là xác định sản phẩm thường mua cùng nhau, mô tả khác biệt hành vi khách hàng và kiểm tra việc kết hợp hai hướng phân tích có giúp hoàn thiện giỏ hàng ngoại tuyến hay không. Đơn vị phân tích luật là hóa đơn; đơn vị phân cụm là khách hàng.',
          '', '1. RQ1: Những luật mua chung nào có đủ bằng chứng và hữu ích trong bài toán hoàn thiện giỏ?',
          '2. RQ2: RFM và K-means tạo ra phân khúc nào, có ổn định và diễn giải được không?',
          '3. RQ3: Luật theo phân khúc khác và có cải thiện so với luật toàn cục trên cùng cohort không?',
          '', '## 2. Dữ liệu và làm sạch','',
          'Nguồn: Chen, D. (2015), Online Retail, UCI Machine Learning Repository, DOI 10.24432/C5BW33, CC BY 4.0. Raw thực tế có 541.909 dòng, 8 cột. Mã hóa đơn/sản phẩm/khách hàng được giữ dạng định danh. Raw được bảo toàn SHA-256.',
          '', 'Policy tách hóa đơn hủy, Quantity/UnitPrice không dương, dịch vụ/voucher/manual adjustment; duplicate hoàn toàn giữ lần đầu theo giả định được ghi rõ. Sản phẩm thực có mã bất thường được xem xét trước khi giữ. Giữ mọi quốc gia và không cắt giao dịch lớn bằng percentile. CustomerID thiếu vẫn được giữ cho luật toàn cục, loại khỏi RFM. Timestamp hóa đơn là dòng muộn nhất để không tách một hóa đơn qua cutoff.',
          '', 'Sau xử lý có 522.537 dòng mua, 19.773 giỏ, 517.289 cặp hóa đơn–sản phẩm. Monetary là tổng mua hàng hóa trước hoàn trả, không phải lợi nhuận hoặc doanh thu ròng. Không dùng trả hàng tương lai để xóa một giao dịch mua quá khứ.',
          '', 'Chi tiết kiểm chứng: [raw audit](../docs/raw_audit_report.md), [policy](../docs/data_preparation_policy.md), [báo cáo chuẩn bị](../docs/data_preparation_report.md).',
          '', '## 3. Thiết kế thời gian và EDA','',
          '| Giai đoạn | Khoảng thời gian | Giỏ | Mục đích |','|---|---|---:|---|',
          '| Train | 01/12/2010–trước 01/08/2011 | 11.044 | Vocabulary, luật, RFM, scaler, K-means |',
          '| Validation | 01/08–trước 01/10/2011 | 3.157 | Chọn tham số luật |',
          '| Test | 01/10–trước 10/12/2011 | 5.572 | Đánh giá cố định một lần |','',
          'EDA trình bày thời gian, phân phối số sản phẩm/giá trị giỏ, sản phẩm phổ biến, quốc gia và RFM. Tháng 12/2011 chỉ đến ngày 09 nên không so tổng tháng như một tháng đầy đủ. Tần suất sản phẩm là số hóa đơn chứa sản phẩm, phân biệt tổng Quantity. Top 10% khách train đóng góp khoảng 58,97% giá trị mua gộp. RFM có đuôi phải dài, nên dùng log1p và chuẩn hóa theo train.',
          '', '![Phân phối RFM train](../results/figures/05_train_rfm_distributions.png)','',
          'EDA/audit mô tả đã xem cấu trúc dữ liệu toàn kỳ; không gọi test là chưa từng xem dưới mọi hình thức. Test không được dùng khai phá luật/chọn K hoặc điều chỉnh ngưỡng. [Bộ hình EDA và nhận xét](../docs/eda_report.md).',
          '', '## 4. Luật kết hợp và so sánh thuật toán','',
          'Mỗi hóa đơn là tập StockCode nhị phân; Quantity không làm một item được tính nhiều lần. Mọi giỏ vẫn nằm trong mẫu số support, kể cả giỏ một sản phẩm. Vocabulary 3.564 sản phẩm chỉ lấy từ train.',
          '', 'Với A→B: support=count(A∪B)/N; confidence=count(A∪B)/count(A); lift=confidence/(count(B)/N). Count được tính lại độc lập bằng bitset Python. Chỉ khai phá sự hiện diện sản phẩm; căn chỉnh ngưỡng đếm do Weka Apriori làm tròn và FP-Growth dùng ceil.',
          '', 'Weka 3.8.7 là backend thực chạy. FP-Growth hoàn tất support 1%, 2%, 5%; Apriori toàn train timeout 45 giây ở 1%/2%, hoàn tất ở 5% với 0 luật. Không dùng kết quả dở hoặc thời gian timeout như một lần hoàn tất. So sánh bổ sung cùng 500 giỏ train cho 800 luật tại 2%, 4 luật tại 5%; hai thuật toán khớp mọi luật/count. Lặp ba lần, báo cáo median. Benchmark đo fit + sinh luật chung; không tách thời gian mining/rules, chưa đo bộ nhớ.',
          '', 'Grid 18 cấu hình gồm support 1/2/5%, tổng chiều dài 2/3, confidence 0,3/0,5/0,7, lift≥1,1 và count≥20. Validation chọn support 1%, chiều dài 2, confidence≥0,3: 738 luật. Ngưỡng support tương ứng tối thiểu 111/11.044 giỏ train.',
          '', '| Luật (tên sản phẩm train) | Count train | Confidence train | Lift train | Count test | Confidence test | Lift test |',
          '|---|---:|---:|---:|---:|---:|---:|']
    seen=set();shown=0
    for row in rules.itertuples():
        pair=tuple(sorted([row.antecedent,row.consequent]))
        if pair in seen:continue
        seen.add(pair)
        main.append(f'| {row.antecedent_names.strip()} → {row.consequent_names.strip()} | {row.count_ab} | {row.confidence:.2%} | {row.lift:.2f} | {row.test_count_ab} | {row.test_confidence:.2%} | {row.test_lift:.2f} |')
        shown+=1
        if shown==5:break
    main += ['', 'Ví dụ các luật liên quan jumbo bag hoặc bộ tách/trà gợi ý khả năng mua kèm trong cùng nhóm hàng. Đây là đồng xuất hiện, chưa chứng minh sản phẩm đầu gây ra việc mua sản phẩm sau. Không ưu tiên chỉ lift cao: bảng luật giữ count, confidence và bằng chứng giai đoạn sau.',
             '', '## 5. RFM và K-means','',
             'R là số ngày từ lần mua cuối đến cutoff 01/08/2011; F là số hóa đơn khác nhau; M là giá trị mua gộp. Ba biến được log1p rồi chuẩn hóa bằng mean/std dân số train. K-means dùng cả ba feature, Euclidean và tắt chuẩn hóa lần hai trong Weka.',
             '', 'Thử K=2–8, 5 nhóm seed, mỗi nhóm 20 khởi tạo K-means++; tổng 700 khởi tạo. Kiểm tra SSE, silhouette toàn bộ khách, ARI giữa seed và quy mô nhỏ nhất. Cần ARI≥0,8 và cụm nhỏ nhất≥3%; chọn silhouette cao nhất, ưu tiên K nhỏ trong biên 0,005. Chọn K=2, mean silhouette 0,4440, mean ARI 0,9954.',
             '', '| Cụm | Khách | Median R (ngày) | Median F | Median M (GBP) | Tỷ trọng giá trị mua gộp |',
             '|---|---:|---:|---:|---:|---:|']
    for row in profile.itertuples():main.append(f'| {row.Segment} | {row.customers:,} | {row.median_recency:.0f} | {row.median_frequency:.0f} | {row.median_monetary:,.2f} | {row.gross_purchase_value_fraction:.2%} |')
    main += ['', 'Segment_1 mua gần đây hơn, thường xuyên hơn và giá trị mua cao hơn; Segment_2 có hành vi ngược lại. Không gọi cụm 2 là churn đã xác minh, không gọi cụm 1 là sinh lợi. PCA chỉ là hình chiếu minh họa; silhouette không phải accuracy với nhãn khách hàng thật.',
             '', '![Hồ sơ cụm](../results/figures/10_segment_profiles.png)','',
             '## 6. Đánh giá ngoại tuyến và kết quả','',
             'Bài toán là hoàn thiện giỏ, không phải dự đoán thứ tự click. Ẩn một sản phẩm/giỏ bằng hash cố định, loại sản phẩm quan sát khỏi gợi ý, dùng popularity train để điền top 5. Giữ target mới ngoài vocabulary trong mẫu số. Các phương án so sánh trên cùng giỏ/target và fallback trong mỗi cohort.',
             '', 'Validation global đạt 13,76% so với popularity 2,79%; đây là tập dùng chọn cấu hình. Sau khóa hash và không refit, kết quả final test:',
             '', *table('all_baskets'),'',
             'So sánh segment trên cùng 3.579 giỏ của khách có hồ sơ train:',
             '',*table('train_profile_customers'),'',
             '![So sánh final test](../results/figures/16_final_test_comparison.png)','',
             'Paired bootstrap 2.000 lần theo CustomerID cho chênh lệch global−popularity là +7,10 điểm phần trăm, CI 95% [+6,34; +7,89]. Chênh lệch segment−global định danh là +0,056 điểm phần trăm, CI [−0,475; +0,600]; chưa có bằng chứng cải thiện bằng phân khúc. Hóa đơn thiếu ID là đơn vị bootstrap riêng. Các CI điều kiện trên model/giai đoạn cố định và chưa điều chỉnh nhiều so sánh.',
             '', '## 7. Trả lời câu hỏi nghiên cứu và ứng dụng','',
             '- **RQ1:** Luật global có bằng chứng đồng xuất hiện và vượt popularity trong bài toán masked-basket test. 689/738 luật có joint count test≥20; 720 có lift test>1. Các con số này mô tả độ ổn định, không phải kiểm định độc lập từng luật.',
             '- **RQ2:** Hai cụm RFM ổn định qua seed và có thể giải thích bằng hành vi gốc. Chúng hỗ trợ mô tả mức hoạt động mua, không xác nhận phân loại churn/lợi nhuận.',
             '- **RQ3:** Chia khách thành cụm không tự bảo đảm cải thiện gợi ý. Validation segment thấp hơn global; test chênh lệch nhỏ và CI chứa 0. Giữ kết luận chưa đủ bằng chứng segment rules tốt hơn.',
             '', 'Có thể dùng luật nhiều bằng chứng để đề xuất vị trí “mua kèm” cho nhóm túi hoặc bộ tách/trà và dùng RFM để mô tả đối tượng thử nghiệm. Cần A/B test theo khách hàng với chỉ tiêu định trước để kiểm tra tác động thực tế. Chưa đề xuất giảm giá cụ thể vì không có biên lợi nhuận/chi phí.',
             '', '## 8. Giới hạn và hướng nghiên cứu sau','',
             'Dữ liệu lịch sử một retailer và tập trung thị trường UK; không tự khái quát sang Việt Nam. Monetary trước hoàn trả có thể bao gồm giao dịch sau đó đã đảo. Duplicate được xử lý theo giả định. Khách thiếu ID không theo dõi được. Mask item không phản ánh luồng tương tác thật. Test có 743/5.183 target mới (14,33%), cao hơn validation 6,39%; model train-only không gợi ý được chúng. Hiệu năng giảm có thể liên quan cơ cấu thời gian/sản phẩm và lựa chọn trên validation, chưa xác định nguyên nhân.',
             '', 'Chưa thử ablation nhiều cách biến đổi/ngoại lệ, thuật toán phân cụm thứ hai, benchmark memory hoặc tách riêng mining/rule time. Hướng sau là đánh giá tái huấn luyện định kỳ trên mốc thời gian mới, so độ nhạy với xử lý hoàn trả và kiểm tra tính hữu ích bằng thử nghiệm thực tế. Không dùng chính test đã chấm để tiếp tục chọn mô hình rồi gọi đó là đánh giá độc lập.',
             '', '## 9. Tái tạo, kiểm chứng và trạng thái bản nộp','',
             'Đã có 24 tests đạt; raw/prepared giữ hash, count luật kiểm tra độc lập, cohort so sánh đồng nhất và source/model/evaluator được khóa trước test. [README](../README.md) hướng dẫn chạy dữ liệu/mô hình. Sau khóa, training runner dừng để bảo toàn artifact; [runner final](../scripts/run_final_evaluation.ps1) kiểm tra kết quả đã lưu và tạo lại tài liệu/hình, không chấm lại.',
             '', 'Các bản chụp train/validation giữ cờ test=false để bảo toàn lịch sử; trạng thái đánh giá hiện hành nằm trong configs/project.json và results/tables/final_test/evaluation_receipt.json. Cần bổ sung rubric, thành viên, định dạng báo cáo, slide và xác nhận yêu cầu nộp; project chưa được xem là đã nộp hoặc bảo vệ xong.',
             '', '## Tài liệu và bằng chứng','',
             '- Chen, D. (2015). Online Retail. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. CC BY 4.0.',
             '- Chen, D., Sain, S. L., & Guo, K. (2012). Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining. Journal of Database Marketing & Customer Strategy Management, 19, 197–208. https://doi.org/10.1057/dbm.2012.17. Ghi chú đọc tại docs/literature_notes.md.',
             '- Weka SimpleKMeans: https://weka.sourceforge.io/doc.stable/weka/clusterers/SimpleKMeans.html.',
             '- Weka FP-Growth: https://weka.sourceforge.io/doc.stable/weka/associations/FPGrowth.html.',
             '- [Báo cáo thực nghiệm train/validation](../docs/experiment_report.md) và [báo cáo final test](../docs/final_evaluation_report.md).',
             '- [Protocol final](../configs/final_evaluation_protocol.json), [freeze lock](../results/models/final_evaluation_lock.json), [receipt](../results/tables/final_test/evaluation_receipt.json).']
    # Add train profiles near the clustering method, before the evaluation section.
    position=main.index('## 5. RFM và K-means')+3
    extra=['', 'K=2–8 được thử bằng 5 nhóm seed 42–46, mỗi nhóm 20 K-means++ starts, tối đa 300 vòng; chọn nghiệm SSE tốt nhất trong mỗi nhóm. Silhouette Euclidean dùng toàn bộ 3.145 khách; kiểm tra ARI giữa nhóm seed và tỷ lệ cụm nhỏ nhất. K hợp lệ cần ARI trung bình≥0,8 và mỗi cụm≥3%; chọn mean silhouette cao nhất, chênh≤0,005 ưu tiên K nhỏ. K=2 có mean silhouette 0,4440, mean ARI 0,9954. Tắt chuẩn hóa nội bộ Weka vì đầu vào đã log-z.',
           '', '| Segment | Khách train | Median R (ngày) | Median F (hóa đơn) | Median M (GBP) | Tỷ trọng mua gộp train |',
           '|---|---:|---:|---:|---:|---:|']
    for row in profile.itertuples():extra.append(f'| {row.Segment} | {row.customers:,} | {row.median_recency:.0f} | {row.median_frequency:.0f} | {row.median_monetary:,.2f} | {row.gross_purchase_value_fraction:.2%} |')
    extra += ['', '![Hồ sơ hai cụm theo RFM gốc](../results/figures/10_segment_profiles.png)', '',
              'Segment_1 mua gần đây hơn, thường xuyên hơn và giá trị mua gộp cao hơn; Segment_2 ít hoạt động hơn trong cửa sổ train. Không gọi đây là nhãn churn hoặc phân loại khả năng sinh lợi. PCA chỉ minh họa; K-means dùng đủ ba đặc trưng.']
    main[position:position]=extra
    related=['', '### Nghiên cứu liên quan','',
             'Chen, Sain và Guo (2012) kết hợp RFM, K-means và diễn giải khách hàng trong dữ liệu bán lẻ. Project kế thừa cách biểu diễn RFM và yêu cầu chuẩn hóa/diễn giải bằng đơn vị gốc, đồng thời bổ sung luật mua chung và kiểm tra theo thời gian. Schema nghiên cứu gốc có trường địa lý khác bản UCI đang dùng; không sao chép số cụm hoặc hiệu năng của nghiên cứu làm kết quả project. Tài liệu Weka cung cấp đặc tả implementation; công thức association rules được đối chiếu với tài liệu mlxtend, dù backend thực chạy là Weka.']
    position=main.index('## 2. Dữ liệu và làm sạch')
    main[position:position]=related+['']
    environment=json.loads((ROOT/'results/tables/model_environment.json').read_text())
    position=main.index('## 9. Tái tạo, kiểm chứng và trạng thái bản nộp')+2
    main[position:position]=[f"Môi trường thực chạy: Python {environment['python']}, Weka {environment['weka_version']}, {environment['java']}; pandas {environment['packages']['pandas']}, NumPy {environment['packages']['numpy']}, ReportLab {environment['packages']['reportlab']}. Thư viện Python được ghi trong requirements-experiments-python.lock.txt; hash Weka jar và môi trường tại results/tables/model_environment.json.",'']
    (ROOT/'report/project_report.md').write_text('\n'.join(main)+'\n',encoding='utf-8')
    print(json.dumps({'reports':['docs/final_evaluation_report.md','report/project_report.md'],
                      'figure':'results/figures/16_final_test_comparison.svg','source_receipt_verified':True}))


if __name__=='__main__':main()
