from __future__ import annotations

from collections.abc import Callable

from fastapi import Request


SUPPORTED_LANGUAGES = {"en", "zh"}
DEFAULT_LANGUAGE = "en"

TRANSLATIONS = {
    "en": {
        "app.subtitle": "Registration ops",
        "nav.dashboard": "Dashboard",
        "nav.tasks": "Tasks",
        "nav.accounts": "Accounts",
        "nav.settings": "Settings",
        "language.english": "English",
        "language.chinese": "中文",
        "dashboard.title": "Dashboard",
        "dashboard.description": "Command center for current runs, queue health, and live logs.",
        "dashboard.running": "Running",
        "dashboard.queued": "Queued Tasks",
        "dashboard.failed": "Failed",
        "dashboard.succeeded": "Succeeded",
        "dashboard.recent_tasks": "Active and Recent Tasks",
        "dashboard.events": "Recent Events",
        "dashboard.id": "ID",
        "dashboard.mode": "Mode",
        "dashboard.status": "Status",
        "dashboard.no_tasks": "No tasks yet.",
        "dashboard.no_events": "No events yet.",
        "accounts.title": "Accounts",
        "accounts.description": "Review produced accounts, OTT upload state, and trial outputs.",
        "accounts.email": "Email",
        "accounts.mode": "Mode",
        "accounts.pool_status": "Pool Status",
        "accounts.trial_url": "Trial URL",
        "accounts.actions": "Actions",
        "accounts.open": "Open",
        "accounts.copy": "Copy",
        "accounts.save": "Save",
        "accounts.delete": "Delete",
        "accounts.edit": "Edit",
        "accounts.trial": "Trial",
        "accounts.push": "Push",
        "accounts.modal_title": "Manage account",
        "accounts.ott": "OTT",
        "accounts.session_token": "Session Token",
        "accounts.label": "Label",
        "accounts.password": "Password",
        "accounts.close": "Close",
        "accounts.empty": "No accounts yet.",
        "accounts.unknown": "unknown",
        "tasks.title": "Tasks",
        "tasks.description": "Create runs, control queue execution, and inspect per-task results.",
        "tasks.docker_limit_title": "Docker runtime limitation",
        "tasks.docker_limit_body": "Docker runtime does not support browser automation flows in v1. Use non-browser modes in this container.",
        "tasks.mode": "Mode",
        "tasks.account_count": "Account Count",
        "tasks.email": "Email",
        "tasks.password": "Password",
        "tasks.generate_trial_link": "Generate trial link",
        "tasks.create": "Create Task",
        "tasks.recent": "Recent Tasks",
        "tasks.placeholder": "Task list will appear here.",
        "settings.title": "Settings",
        "settings.description": "Environment readiness for YYDS Mail, Pool API, and trial generation.",
    },
    "zh": {
        "app.subtitle": "注册运营台",
        "nav.dashboard": "概览",
        "nav.tasks": "任务",
        "nav.accounts": "账号",
        "nav.settings": "设置",
        "language.english": "English",
        "language.chinese": "中文",
        "dashboard.title": "概览",
        "dashboard.description": "查看当前运行、队列状态和最近日志。",
        "dashboard.running": "运行中",
        "dashboard.queued": "排队任务",
        "dashboard.failed": "失败",
        "dashboard.succeeded": "成功",
        "dashboard.recent_tasks": "最近任务",
        "dashboard.events": "最近事件",
        "dashboard.id": "编号",
        "dashboard.mode": "模式",
        "dashboard.status": "状态",
        "dashboard.no_tasks": "暂无任务。",
        "dashboard.no_events": "暂无事件。",
        "accounts.title": "账号",
        "accounts.description": "管理已生成账号、Pool 状态和 Trial 链接。",
        "accounts.email": "邮箱",
        "accounts.mode": "模式",
        "accounts.pool_status": "Pool 状态",
        "accounts.trial_url": "Trial 链接",
        "accounts.actions": "操作",
        "accounts.open": "打开",
        "accounts.copy": "复制",
        "accounts.save": "保存",
        "accounts.delete": "删除",
        "accounts.edit": "编辑",
        "accounts.trial": "Trial",
        "accounts.push": "推送",
        "accounts.modal_title": "管理账号",
        "accounts.ott": "OTT",
        "accounts.session_token": "Session Token",
        "accounts.label": "标签",
        "accounts.password": "密码",
        "accounts.close": "关闭",
        "accounts.empty": "暂无账号。",
        "accounts.unknown": "未知",
        "tasks.title": "任务",
        "tasks.description": "创建运行任务、控制队列并查看任务结果。",
        "tasks.docker_limit_title": "Docker 运行限制",
        "tasks.docker_limit_body": "当前 Docker 运行环境暂不支持浏览器自动化流程，请使用非浏览器模式。",
        "tasks.mode": "模式",
        "tasks.account_count": "账号数量",
        "tasks.email": "邮箱",
        "tasks.password": "密码",
        "tasks.generate_trial_link": "生成 Trial 链接",
        "tasks.create": "创建任务",
        "tasks.recent": "最近任务",
        "tasks.placeholder": "任务列表会显示在这里。",
        "settings.title": "设置",
        "settings.description": "检查 YYDS Mail、Pool API 和 Trial 生成配置。",
    },
}


def resolve_language(request: Request) -> str:
    requested = request.query_params.get("lang") or request.cookies.get("wa_lang")
    return requested if requested in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def translator(lang: str) -> Callable[[str], str]:
    catalog = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])

    def translate(key: str) -> str:
        return catalog.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))

    return translate
