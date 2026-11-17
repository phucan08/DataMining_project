"""Generate the preparation report from recorded outputs, without refitting anything."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    from report_documentation import retain_frozen_english_reports
    if retain_frozen_english_reports(ROOT,['docs/data_preparation_report.md']):
        return
    tables = ROOT / "results/tables"
    data = ROOT / "data/processed"
    summary = json.loads((tables / "preparation_summary.json").read_text(encoding="utf-8"))
    investigation = json.loads((tables / "anomaly_investigation.json").read_text(encoding="utf-8"))
    transform = json.loads((data / "rfm_transform.json").read_text(encoding="utf-8"))
    matrices = json.loads((data / "basket_matrix_metadata.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "configs/cleaning_policy.json").read_text(encoding="utf-8"))
    count = lambda value: f"{int(value):,}"
    labels = {
        "invalid_required_fields": "Thiếu/sai trường bắt buộc",
        "exact_duplicate": "Trùng hoàn toàn tám cột gốc",
        "invoice_identity_or_calendar_conflict": "Hóa đơn xung đột ID/quốc gia/ngày",
        "cancelled_invoice": "Hóa đơn C/c",
        "nonpositive_quantity": "Quantity không dương còn lại",
        "nonpositive_unit_price": "UnitPrice không dương còn lại",
        "non_merchandise_or_ancillary_code": "Phí/voucher/manual/mẫu-phụ trợ",
        "unreviewed_stock_code": "Mã hàng chưa duyệt",
    }
    lines = [
        "# Báo cáo làm sạch và tạo dữ liệu giỏ hàng/RFM",
        "",
        f"Trạng thái: pipeline đã chạy trên workbook thực, kiểm tra hash raw và đối chiếu tổng đã đạt. Thời điểm tạo số liệu (UTC): {summary['generated_at_utc']}.",
        "",
        "## 1. Kết quả chính",
        "",
        "| Chỉ tiêu | Giá trị |",
        "|---|---:|",
        f"| Dòng raw | {count(summary['raw_rows'])} |",
        f"| Dòng mua hàng hóa hợp lệ theo policy | {count(summary['clean_purchase_rows'])} |",
        f"| Dòng tách khỏi nhánh mua, vẫn giữ ledger/raw | {count(summary['excluded_rows'])} |",
        f"| Giỏ hàng toàn kỳ | {count(summary['clean_purchase_invoices'])} |",
        f"| Mã hàng hóa toàn kỳ | {count(summary['clean_product_ids'])} |",
        f"| CustomerID không thiếu toàn kỳ sau làm sạch | {count(summary['clean_known_customer_ids'])} |",
        f"| Dòng mua thiếu CustomerID được giữ cho basket | {count(summary['clean_rows_missing_customer_id'])} |",
        f"| Cặp hóa đơn–sản phẩm nhị phân toàn kỳ | {count(summary['basket_item_pairs'])} |",
        f"| Khách train có hồ sơ RFM | {count(summary['rfm_train_customers'])} |",
        f"| Vocabulary sản phẩm học từ train | {count(summary['train_product_vocabulary'])} |",
        "",
        "Chênh lệch giữa số khách toàn kỳ và RFM là do RFM chỉ dùng khách có ID trong train, không dùng thông tin validation/test. Chưa chạy Apriori, FP-Growth hoặc K-means.",
        "",
        "## 2. Nhật ký làm sạch có thứ tự",
        "",
        "| Bước | Dòng trước | Dòng tách tại bước này | Dòng sau | Hóa đơn sau | Khách có ID sau |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in csv_rows(tables / "cleaning_log.csv"):
        lines.append(f"| {labels.get(row['stage'], row['stage'])} | {count(row['rows_before'])} | {count(row['rows_removed'])} | {count(row['rows_after'])} | {count(row['invoices_after'])} | {count(row['identified_customers_after'])} |")
    lines += [
        "",
        "Mỗi dòng tách chỉ được gán lý do đầu tiên theo thứ tự trên nên có thể cộng cột dòng tách. Các số audit thô trước đó có thể giao nhau; không cộng trực tiếp chúng. Quyết định giữ/loại và giả định được mô tả trong [data_preparation_policy.md](data_preparation_policy.md).",
        "",
        "## 3. Các nhóm bất thường và quyết định",
        "",
        f"- {count(investigation['invoice_ids_with_multiple_times'])} hóa đơn nhiều timestamp chỉ lệch tối đa {investigation['max_invoice_span_minutes']:g} phút, không qua ngày. Dùng thời điểm cuối cùng và giữ hóa đơn nguyên vẹn khi chia split.",
        f"- {count(investigation['nonstandard_stockcodes'])} mã ngoài cấu trúc chuẩn được xem xét. Giữ bảy mã DCGS hàng hóa đã duyệt, tách phí/voucher/mẫu và bút toán không xác định sản phẩm; không còn mã mua dương chưa duyệt.",
        "- Exact duplicates được giữ lần đầu như một giả định phân tích; raw và excluded_lines lưu đầy đủ để thay đổi lựa chọn khi cần. Các dòng cùng sản phẩm nhưng khác thông tin hợp lệ vẫn được cộng Quantity/giá trị.",
        "- Không điền CustomerID giả; giữ mọi quốc gia và không cắt giao dịch lớn theo percentile. Giữ basket một sản phẩm trong mẫu số support.",
        "",
        "### Hoàn trả và giới hạn Monetary",
        "",
        "Monetary là giá trị mua hàng hóa trước hoàn trả, không phải doanh thu ròng/lợi nhuận. Trong mười dòng có Quantity mua lớn nhất, tìm thấy các đối ứng đảo lượng sau thời điểm mua như sau; đây chỉ là kiểm tra mẫu, không phải hệ thống ghép toàn bộ hoàn trả:",
        "",
        "| Hóa đơn mua | Hóa đơn đối ứng | Mã hàng | Quantity mua | Phút sau mua | Giá trị mua GBP |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in csv_rows(tables / "anomaly_extreme_purchase_return_evidence.csv"):
        lines.append(f"| {row['PurchaseInvoiceNo']} | {row['ReturnInvoiceNo']} | {row['StockCode']} | {count(row['Quantity'])} | {float(row['MinutesUntilReturn']):,.0f} | {float(row['PurchaseValueGBP']):,.2f} |")
    lines += [
        "",
        "Không dùng trả hàng tương lai để xóa mua quá khứ. Vì dùng gross purchases, khách đã trả lại hàng vẫn có thể có Monetary cao; tên cụm sau này phải phản ánh chi tiêu mua gộp, không mặc định khách sinh lợi hoặc không hoàn trả. Bảng đối ứng chỉ nằm ở phần điều tra, không được đưa vào feature train.",
        "",
        "## 4. Chia thời gian và cohort",
        "",
        f"- Train: [{policy['time_split']['train_start']}, {policy['time_split']['train_end_exclusive']}).",
        f"- Validation: [{policy['time_split']['train_end_exclusive']}, {policy['time_split']['validation_end_exclusive']}).",
        f"- Test: [{policy['time_split']['validation_end_exclusive']}, {policy['time_split']['test_end_exclusive']}).",
        "",
        "| Split | Dòng mua | Giỏ hàng | Khách có ID | Giỏ một sản phẩm | ID mới so với train |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["cohorts"]:
        lines.append(f"| {row['split']} | {count(row['purchase_lines'])} | {count(row['invoices'])} | {count(row['identified_customers'])} | {count(row['single_item_baskets'])} | {count(row['new_identified_customer_ids_vs_train'])} |")
    lines += [
        "",
        "Toàn bộ dòng nguồn của train đều trước cutoff. Đã xem chất lượng dữ liệu toàn kỳ nhưng chưa chọn tham số từ kết quả mô hình trên test. Chỉ cohort khách có hồ sơ train mới được gán phân khúc cũ khi đánh giá ở giai đoạn sau; khách mới và khách thiếu ID phải có nhánh fallback/báo cáo riêng.",
        "",
        "## 5. Ma trận giỏ hàng và sản phẩm mới",
        "",
        "| Split | Số hàng | Cột train | Phần tử 1 | Cặp sản phẩm ngoài vocabulary | Giỏ không có item train |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, matrix in matrices.items():
        lines.append(f"| {name} | {count(matrix['rows'])} | {count(matrix['columns'])} | {count(matrix['nonzero_entries'])} | {count(matrix['unknown_train_product_pairs'])} | {count(matrix['rows_with_no_known_train_product'])} |")
    lines += [
        "",
        "Long-table basket_items giữ mọi sản phẩm. Ma trận dùng vocabulary train và giữ row mapping cho mọi giỏ, kể cả row không còn item nào trong vocabulary. Các mảng tọa độ NPZ là format riêng của project, không phải file do scipy.sparse.save_npz tạo.",
        "",
        "## 6. RFM train và biến đổi",
        "",
        f"Reference date (exclusive) = {summary['rfm_reference_date']}; tổng Monetary đối chiếu từ hóa đơn train có ID = {summary['train_rfm_purchase_value_gbp']:,.2f} GBP.",
        "",
        "Frequency đếm hóa đơn khác nhau; Recency đếm ngày lịch; Monetary cộng giá trị hàng hóa hợp lệ. Các ví dụ được kiểm tra lại trực tiếp từ purchase_lines:",
        "",
        "| CustomerID | Recency, ngày | Frequency, hóa đơn | Monetary GBP |",
        "|---|---:|---:|---:|",
    ]
    for row in csv_rows(tables / "rfm_spot_checks.csv"):
        lines.append(f"| {row['CustomerID']} | {count(row['Recency'])} | {count(row['Frequency'])} | {float(row['MonetaryGBP']):,.2f} |")
    lines += [
        "",
        "Độ lệch phải ở RFM train trước biến đổi:",
        "",
        "| Biến | Skewness train | Mean sau log1p | Population scale sau log1p |",
        "|---|---:|---:|---:|",
    ]
    for column in ["Recency", "Frequency", "Monetary"]:
        lines.append(f"| {column} | {transform['raw_train_skewness'][column]:.4f} | {transform['log_means'][column]:.6f} | {transform['log_population_scales'][column]:.6f} |")
    lines += [
        "",
        "Lưu RFM gốc và đặc trưng log1p rồi chuẩn hóa ddof=0. Tham số chỉ fit trên khách train, không dùng validation/test. Đây là cấu hình chuẩn bị đầu tiên; chưa chứng minh nó tối ưu cho phân cụm và chưa chọn K.",
        "",
        "## 7. Đầu ra để sử dụng",
        "",
        "| Tệp trong data/processed | Ý nghĩa |",
        "|---|---|",
        "| purchase_lines.csv.gz | Dòng mua hàng hóa hợp lệ; giữ SourceRow, timestamp nguồn, timestamp hóa đơn, split và tiền chính xác |",
        "| excluded_lines.csv.gz | Dòng tách khỏi nhánh mua, kèm FirstExclusionReason |",
        "| returns_adjustments_raw.csv.gz | Ledger raw của hủy/Quantity không dương/giá không dương; có thể giao với excluded_lines, không cộng hai bảng |",
        "| baskets.csv | Một dòng mỗi hóa đơn; cohort ID và khả năng có hồ sơ train |",
        "| basket_items.csv.gz | Một dòng mỗi InvoiceNo–StockCode, Present=1; có cả sản phẩm mới |",
        "| product_catalog_train.csv | ColumnIndex và tên sản phẩm chọn chỉ từ train |",
        "| basket_*_coordinates.npz | row_indices, column_indices, values, shape cho từng split |",
        "| basket_*_row_index.csv | Ánh xạ RowIndex sang InvoiceNo cho từng split |",
        "| basket_matrix_metadata.json | Hình dạng, số phần tử, sản phẩm mới và row rỗng theo vocabulary train |",
        "| rfm_train.csv | CustomerID, R/F/M gốc, tiền số nguyên và LastPurchase |",
        "| rfm_train_features.csv | CustomerID và RecencyLogZ, FrequencyLogZ, MonetaryLogZ |",
        "| rfm_transform.json | Cutoff, tham số biến đổi và thống kê train |",
        "| prepared_manifest.json | SHA-256 dữ liệu dẫn xuất và liên kết hash raw/policy |",
        "",
        "Các bằng chứng trong results/tables gồm cleaning_log.csv, prepared_cohort_summary.csv, preparation_summary.json, rfm_train_summary.csv và các bảng spot checks/điều tra.",
        "",
        "## 8. Kiểm chứng và tái tạo",
        "",
        "Pipeline đã đối chiếu: raw = clean + excluded; số cặp item bằng tổng UniqueProducts; tiền dòng hàng = tiền giỏ; tiền RFM = tiền hóa đơn train đủ ID; mỗi hóa đơn chỉ có một split; toàn bộ timestamp nguồn train trước cutoff; raw SHA-256 không đổi.",
        "",
        "Chạy `& .\\scripts\\run_preparation.ps1` để tái tạo. Test suite có các tình huống ranh giới cutoff, khách thiếu ID, sản phẩm tương lai, dòng hàng lặp, xung đột hóa đơn và ảnh hưởng của giao dịch/hoàn trả tương lai. Việc chuẩn bị chưa cần scikit-learn/mlxtend; bước mô hình tiếp theo vẫn cần bổ sung thư viện hoặc môi trường tương ứng.",
    ]
    output = ROOT / "docs/data_preparation_report.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    main()
