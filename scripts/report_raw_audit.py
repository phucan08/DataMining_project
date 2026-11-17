"""Build the readable raw-audit report from observed JSON/CSV outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from report_documentation import retain_frozen_english_reports
    if retain_frozen_english_reports(ROOT,['docs/raw_audit_report.md']):
        return
    tables = ROOT / "results" / "tables"
    metrics = json.loads((tables / "raw_audit.json").read_text(encoding="utf-8"))
    source = json.loads((ROOT / "data" / "raw" / "source_metadata.json").read_text(encoding="utf-8"))
    environment = json.loads((tables / "environment.json").read_text(encoding="utf-8"))
    with (tables / "raw_schema.csv").open(encoding="utf-8-sig", newline="") as stream:
        schema = list(csv.DictReader(stream))
    with (tables / "raw_monthly_counts.csv").open(encoding="utf-8-sig", newline="") as stream:
        months = list(csv.DictReader(stream))
    with (tables / "raw_country_counts.csv").open(encoding="utf-8-sig", newline="") as stream:
        countries = list(csv.DictReader(stream))
    with (tables / "raw_numeric_summary.csv").open(encoding="utf-8-sig", newline="") as stream:
        numeric = {row["statistic"]: row for row in csv.DictReader(stream)}
    count = lambda n: f"{int(n):,}"
    percent = lambda n: f"{100 * int(n) / metrics['rows']:.2f}%"
    lines = [
        "# Báo cáo raw audit — UCI Online Retail",
        "",
        "Trạng thái: đã đọc workbook thực và lưu thống kê; chưa loại dòng, điền thiếu, gộp giỏ hàng hoặc huấn luyện mô hình.",
        "",
        "## 1. Nguồn và tính toàn vẹn",
        "",
        f"- Nguồn: {source['landing_page']}.",
        f"- URL tải gốc: {source['download_url']}.",
        "- File ZIP được tải từ nút Download trên website UCI, sao chép vào data/raw sau khi tải hoàn tất và vượt kiểm tra CRC ZIP.",
        f"- Thời điểm lập metadata nguồn (UTC): {source['retrieved_at_utc']}.",
        "- Giấy phép: CC BY 4.0; giữ nguyên archive và workbook, lưu SHA-256 để kiểm tra lại.",
        "",
        "| Tệp | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for record in source["files"]:
        lines.append(f"| {record['name']} | {count(record['size_bytes'])} | `{record['sha256']}` |")
    lines += [
        "",
        f"SHA-256 workbook ở bước audit là `{metrics['input_sha256']}`; script kiểm tra lại sau khi tính thống kê để phát hiện thay đổi giữa chừng.",
        "",
        "## 2. Tổng quan thực đo",
        "",
        "| Chỉ tiêu | Kết quả |",
        "|---|---:|",
        f"| Dòng giao dịch sản phẩm | {count(metrics['rows'])} |",
        f"| Cột | {len(metrics['columns'])} |",
        f"| Mã hóa đơn khác nhau, gồm hủy | {count(metrics['distinct_invoice_ids'])} |",
        f"| Mã sản phẩm khác nhau, chưa loại mã dịch vụ | {count(metrics['distinct_product_ids'])} |",
        f"| CustomerID khác nhau không thiếu | {count(metrics['distinct_identified_customer_ids'])} |",
        f"| Quốc gia | {count(metrics['distinct_countries'])} |",
        f"| Thời điểm đầu | {metrics['date_min']} |",
        f"| Thời điểm cuối | {metrics['date_max']} |",
        "",
        "Một dòng là một dòng hàng, không phải một giỏ hàng. Chưa có bộ giao dịch mua hợp lệ, vì vậy không diễn giải các tổng raw là số đơn mua hoàn tất. Giá nguồn dùng GBP; chưa suy ra timezone cho timestamp.",
        "",
        "## 3. Schema và missing values",
        "",
        "| Cột | Kiểu sau đọc | Thiếu | Tỷ lệ thiếu | Giá trị khác nhau không thiếu |",
        "|---|---|---:|---:|---:|",
    ]
    for row in schema:
        lines.append(f"| {row['column']} | {row['dtype']} | {count(row['missing'])} | {percent(row['missing'])} | {count(row['unique_nonmissing'])} |")
    lines += [
        "",
        "CustomerID được đọc dưới dạng mã chuỗi nullable, không điền một mã khách giả. Các dòng thiếu ID phải được tách khỏi nhánh RFM; khả năng giữ cho luật toàn cục cần xem xét sau khi xử lý hóa đơn. Description không phải khóa sản phẩm.",
        "",
        "## 4. Các vấn đề dữ liệu",
        "",
        "| Kiểm tra | Số lượng | Đơn vị |",
        "|---|---:|---|",
    ]
    checks = [
        ("Dòng trùng hoàn toàn sau lần xuất hiện đầu", "exact_duplicate_rows_after_first", "dòng"),
        ("Cặp InvoiceNo–StockCode lặp sau lần đầu", "repeated_invoice_product_rows_after_first", "dòng"),
        ("StockCode có nhiều Description không thiếu", "product_ids_with_multiple_nonmissing_descriptions", "mã sản phẩm"),
        ("InvoiceNo bắt đầu bằng C/c", "cancelled_invoice_rows", "dòng"),
        ("Quantity âm", "quantity_negative_rows", "dòng"),
        ("Quantity bằng 0", "quantity_zero_rows", "dòng"),
        ("UnitPrice âm", "unit_price_negative_rows", "dòng"),
        ("UnitPrice bằng 0", "unit_price_zero_rows", "dòng"),
        ("Ngày không thiếu nhưng parse không được", "invalid_nonmissing_dates", "dòng"),
        ("Quantity không thiếu nhưng không phải số", "invalid_nonmissing_quantity", "dòng"),
        ("UnitPrice không thiếu nhưng không phải số", "invalid_nonmissing_unit_price", "dòng"),
        ("InvoiceNo gắn với nhiều CustomerID không thiếu", "invoice_ids_with_multiple_nonmissing_customers", "mã hóa đơn"),
        ("InvoiceNo có nhiều timestamp", "invoice_ids_with_multiple_timestamps", "mã hóa đơn"),
    ]
    for label, key, unit in checks:
        lines.append(f"| {label} | {count(metrics[key])} | {unit} |")
    lines += [
        "",
        "Các nhóm kiểm tra giao nhau, không cộng chúng để tính số dòng sẽ bị loại. Cặp hóa đơn–sản phẩm lặp không mặc nhiên là lỗi: khi tạo giỏ nhị phân chỉ cần xét có/không, nhưng khi tính tiền phải có chính sách gộp/khử trùng riêng.",
        "",
        f"Có {count(metrics['invoice_ids_with_multiple_timestamps'])} mã hóa đơn nhiều timestamp. Cần kiểm tra độ lệch và chọn quy tắc thời điểm cấp hóa đơn trước khi chia dữ liệu; không tách các dòng cùng hóa đơn sang hai giai đoạn.",
        "",
        "## 5. Phạm vi thời gian và quốc gia",
        "",
        "| Tháng | Dòng raw | Mã hóa đơn trong tháng |",
        "|---|---:|---:|",
    ]
    for row in months:
        lines.append(f"| {row['month']} | {count(row['rows'])} | {count(row['invoices'])} |")
    lines += [
        "",
        "Tháng 12/2011 chỉ có dữ liệu đến 09/12; không so tổng tháng này trực tiếp với một tháng đầy đủ. Số hóa đơn theo tháng là số mã xuất hiện trong tháng, chưa phải một phép phân bổ hóa đơn chuẩn hóa theo timestamp đại diện.",
        "",
        "| Quốc gia có nhiều dòng nhất | Dòng raw | Tỷ lệ dòng |",
        "|---|---:|---:|",
    ]
    for row in countries[:5]:
        lines.append(f"| {row['Country']} | {count(row['rows'])} | {percent(row['rows'])} |")
    lines += [
        "",
        "Bảng đầy đủ nằm ở results/tables/raw_country_counts.csv. Chưa khóa country filter; dữ liệu raw của mọi quốc gia vẫn được giữ.",
        "",
        "## 6. Giá trị và ngoại lệ cần điều tra",
        "",
        "| Biến raw | Min | Median | P99 | Max |",
        "|---|---:|---:|---:|---:|",
    ]
    for column in ["Quantity", "UnitPrice", "RawLineValue"]:
        values = [numeric[index][column] for index in ["min", "50%", "99%", "max"]]
        lines.append(f"| {column} | " + " | ".join(f"{float(value):,.2f}" for value in values) + " |")
    lines += [
        "",
        "RawLineValue = Quantity × UnitPrice trên raw, gồm cả hủy/trả/điều chỉnh; chưa dùng làm Monetary hoặc doanh thu. Giá trị lớn có thể thuộc khách mua sỉ, cần điều tra trước khi coi là lỗi hoặc cắt theo percentile.",
        "",
        "## 7. Bước xử lý đề xuất tiếp theo — chưa thực hiện",
        "",
        "1. Kiểm tra mẫu của các nhóm hủy/trả, giá không dương, mã phí/dịch vụ và cặp dòng lặp; chốt chính sách có bằng chứng.",
        "2. Phân tách tập mua hợp lệ cho basket và tập khách định danh cho RFM; báo cáo mức dữ liệu bị loại theo từng bước.",
        "3. Kiểm tra hóa đơn nhiều timestamp và tên sản phẩm không nhất quán trước khi chốt khóa thời gian/tên hiển thị.",
        "4. Sau đó chọn cohort quốc gia và các mốc thời gian; học phép biến đổi và mô hình chỉ trên giai đoạn discovery/train.",
        "5. Chưa khai phá luật, phân cụm hoặc đặt trước số dòng sạch, số cụm và số luật phải đạt.",
        "",
        "## 8. Tái tạo kết quả",
        "",
        "Từ thư mục project, chạy `& .\\scripts\\run_raw_audit.ps1`. Script chọn Python có đủ pandas/numpy/openpyxl, kiểm tra SHA-256 raw, ghi môi trường và tái tạo bảng audit/báo cáo.",
        "",
        f"Python đã sử dụng: {environment['python']}; pandas {environment['packages']['pandas']}; numpy {environment['packages']['numpy']}; openpyxl {environment['packages']['openpyxl']}.",
        "",
        "Môi trường này đủ cho raw audit. scikit-learn/mlxtend và thư viện vẽ chưa có trong runtime đang ghi nhận; chưa đánh dấu môi trường modeling hoàn thành.",
        "",
        "Các bảng bằng chứng: raw_audit.json, raw_schema.csv, raw_monthly_counts.csv, raw_country_counts.csv, raw_numeric_summary.csv trong results/tables. Không có dòng raw nào bị sửa hoặc loại trong bước này.",
    ]
    output = ROOT / "docs" / "raw_audit_report.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    main()
