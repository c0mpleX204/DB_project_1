#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from urllib import error, parse, request


SESSION_FILE = Path(".cli_session.json")


def print_ok(message: str):
    print(f"[OK] {message}")


def print_info(message: str):
    print(f"[INFO] {message}")


def print_warn(message: str):
    print(f"[WARN] {message}")


def print_error(message: str):
    print(f"[ERROR] {message}")


def print_table(headers: list[str], rows: list[list[object]]):
    text_rows = [["" if c is None else str(c) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in text_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_line = "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"

    print(sep)
    print(header_line)
    print(sep)
    for row in text_rows:
        print("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    print(sep)


def api_request(base_url: str, path: str, method: str = "GET", payload=None, passenger_id: int | None = None):
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    if passenger_id:
        headers["X-Passenger-Id"] = str(passenger_id)

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                raise RuntimeError("Empty response from server")
            return json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        detail = f"HTTP {exc.code}"
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    detail=str(parsed.get("detail", detail))
                else:
                    detail=body
            except Exception:
                detail = body
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError(f"API unreachable: {exc.reason}") from exc


def save_session(passenger_id: int):
    SESSION_FILE.write_text(json.dumps({"passenger_id": passenger_id}, ensure_ascii=False), encoding="utf-8")


def load_session_passenger_id() -> int | None:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        passenger_id = int(data.get("passenger_id", 0))
        return passenger_id if passenger_id > 0 else None
    except Exception:
        return None


def require_passenger_id(args) -> int:
    if args.passenger_id:
        return args.passenger_id
    session_id = load_session_passenger_id()
    if session_id:
        return session_id
    raise ValueError("passenger_id missing. Please login first or pass --passenger-id.")


def cmd_login(args):
    data = api_request(
        args.base_url,
        "/api/v1/auth/login",
        method="POST",
        payload={
            "username": args.mobile_number,
            "password": args.password,
        },
    )
    passenger_id = int(data["passenger_id"])
    save_session(passenger_id)
    print_ok(f"登录成功 passenger_id={passenger_id}")


def cmd_logout(_args):
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print_ok("退出登录成功")
        return
    print_info("当前没有登录会话")


def cmd_generate(args):
    data = api_request(
        args.base_url,
        "/api/v1/tickets/generate",
        method="POST",
        payload={
            "start_date": args.start_date,
            "end_date": args.end_date,
        },
    )
    print_ok(f"自动生成机票完成，新增 {data['added']} 条")


def cmd_search(args):
    params = {
        "departure_city": args.departure_city,
        "arrival_city": args.arrival_city,
        "flight_date": args.date,
        "limit": 200,
        "offset": 0,
    }
    if args.airline:
        params["airline"] = args.airline
    if args.departure_time:
        params["departure_time"] = args.departure_time
    if args.arrival_time:
        params["arrival_time"] = args.arrival_time

    q = parse.urlencode(params)
    rows = api_request(args.base_url, f"/api/v1/tickets/search?{q}")
    if not rows:
        print_info("没有符合条件的机票")
        return

    headers = [
        "ticket_id",
        "flight",
        "airline",
        "route",
        "dep_time",
        "arr_time",
        "date",
        "eco(价/余)",
        "biz(价/余)",
    ]
    table_rows: list[list[object]] = []
    for r in rows:
        table_rows.append(
            [
                r["ticket_id"],
                r["flight_number"],
                f"{r['airline_code']}({r['airline_name']})",
                f"{r['source_city']}({r['source_iata']})->{r['destination_city']}({r['destination_iata']})",
                r["departure_time_local"],
                f"{r['arrival_time_local']}(+{r['arrival_day_offset']})",
                r["flight_date"],
                f"{r['economy_price']}/{r['economy_remain']}",
                f"{r['business_price']}/{r['business_remain']}",
            ]
        )

    print_table(headers, table_rows)
    print_ok(f"共查询到 {len(rows)} 条机票")


def cmd_book(args):
    passenger_id = require_passenger_id(args)
    data = api_request(
        args.base_url,
        "/api/v1/orders/book",
        method="POST",
        passenger_id=passenger_id,
        payload={
            "passenger_id": passenger_id,
            "ticket_id": args.ticket_id,
            "cabin_class": args.cabin_class,
        },
    )
    print_ok(f"下单成功 order_id={data['order_id']} booked_at={data['booked_at']}")


def cmd_orders(args):
    passenger_id = require_passenger_id(args)
    rows = api_request(
        args.base_url,
        f"/api/v1/orders/{passenger_id}?limit=200&offset=0",
        passenger_id=passenger_id,
    )
    if not rows:
        print_info("当前用户暂无订单")
        return

    headers = ["order_id", "status", "class", "price", "flight", "route", "date", "booked_at"]
    table_rows: list[list[object]] = []
    for r in rows:
        table_rows.append(
            [
                r["order_id"],
                r["status"],
                r["cabin_class"],
                r["unit_price"],
                r["flight_number"],
                f"{r['source_city']}->{r['destination_city']}",
                r["flight_date"],
                r["booked_at"],
            ]
        )
    print_table(headers, table_rows)
    print_ok(f"共查询到 {len(rows)} 条订单")


def cmd_cancel(args):
    passenger_id = require_passenger_id(args)
    data = api_request(
        args.base_url,
        f"/api/v1/orders/{passenger_id}/{args.order_id}/cancel",
        method="POST",
        passenger_id=passenger_id,
    )
    print_ok(f"取消成功 order_id={data['order_id']} status={data['status']}")


def run_interactive_menu(args):
    print_info("=== CS307 DB Project CLI (Interactive) ===")
    print_info(f"API: {args.base_url}")

    while True:
        current_id = load_session_passenger_id()
        print("\n请选择操作:")
        print("1) 登录")
        print("2) 搜索机票")
        print("3) 下单")
        print("4) 查看我的订单")
        print("5) 取消订单")
        print("6) 退出登录")
        print("0) 退出程序")
        if current_id:
            print_info(f"当前登录 passenger_id={current_id}")
        else:
            print_warn("当前未登录")

        choice = input("输入编号: ").strip()

        try:
            if choice == "1":
                mobile = input("手机号: ").strip()
                password = input("密码: ").strip()
                cmd_login(argparse.Namespace(base_url=args.base_url, mobile_number=mobile, password=password))
            elif choice == "2":
                departure_city = input("出发城市: ").strip()
                arrival_city = input("到达城市: ").strip()
                date = input("日期(YYYY-MM-DD): ").strip()
                airline = input("航司(可选, 回车跳过): ").strip() or None
                departure_time = input("出发时间下限(可选 HH:MM): ").strip() or None
                arrival_time = input("到达时间上限(可选 HH:MM): ").strip() or None
                cmd_search(
                    argparse.Namespace(
                        base_url=args.base_url,
                        departure_city=departure_city,
                        arrival_city=arrival_city,
                        date=date,
                        airline=airline,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                    )
                )
            elif choice == "3":
                ticket_id = int(input("ticket_id: ").strip())
                cabin_class = input("舱位(economy/business): ").strip()
                cmd_book(
                    argparse.Namespace(
                        base_url=args.base_url,
                        passenger_id=None,
                        ticket_id=ticket_id,
                        cabin_class=cabin_class,
                    )
                )
            elif choice == "4":
                cmd_orders(argparse.Namespace(base_url=args.base_url, passenger_id=None))
            elif choice == "5":
                order_id = int(input("order_id: ").strip())
                cmd_cancel(
                    argparse.Namespace(
                        base_url=args.base_url,
                        passenger_id=None,
                        order_id=order_id,
                    )
                )
            elif choice == "6":
                cmd_logout(argparse.Namespace())
            elif choice == "0":
                print_info("已退出程序")
                break
            else:
                print_warn("无效选项，请重新输入")
        except Exception as exc:
            print_error(str(exc))


def build_parser():
    parser = argparse.ArgumentParser(description="CS307 DB Project CLI (API mode)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")

    sub = parser.add_subparsers(dest="cmd", required=False)

    p = sub.add_parser("login", help="Login with mobile_number and password")
    p.add_argument("--mobile-number", required=True)
    p.add_argument("--password", required=True)
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("logout", help="Clear local login session")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("generate", help="Generate ticket inventory for date range")
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("search", help="Search tickets")
    p.add_argument("--departure-city", required=True)
    p.add_argument("--arrival-city", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--airline")
    p.add_argument("--departure-time")
    p.add_argument("--arrival-time")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("book", help="Book one ticket")
    p.add_argument("--passenger-id", type=int)
    p.add_argument("--ticket-id", type=int, required=True)
    p.add_argument("--cabin-class", choices=["economy", "business"], required=True)
    p.set_defaults(func=cmd_book)

    p = sub.add_parser("orders", help="List passenger orders")
    p.add_argument("--passenger-id", type=int)
    p.set_defaults(func=cmd_orders)

    p = sub.add_parser("cancel", help="Cancel one order")
    p.add_argument("--passenger-id", type=int)
    p.add_argument("--order-id", type=int, required=True)
    p.set_defaults(func=cmd_cancel)

    p = sub.add_parser("menu", help="Start interactive CLI menu")
    p.set_defaults(func=run_interactive_menu)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if not getattr(args, "cmd", None):
            run_interactive_menu(args)
            return
        args.func(args)
    except Exception as exc:
        print_error(str(exc))


if __name__ == "__main__":
    main()
