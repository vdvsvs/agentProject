from getpass import getpass

import keyring

from knowledge_agent import load_model_config


def main() -> None:
    credential_name = load_model_config()["credential_name"]
    api_key = getpass("请输入 API Key（输入不会显示）：").strip()
    if not api_key:
        raise SystemExit("API Key 不能为空")

    keyring.set_password("knowledge-agent", credential_name, api_key)
    print(f"已保存到 Windows Credential Manager：{credential_name}")


if __name__ == "__main__":
    main()
