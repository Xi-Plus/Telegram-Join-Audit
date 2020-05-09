# Telegram-Join-Audit

## Command
### User
#### Any text
回應各狀態的預設訊息

#### /request
在 `new` 及 `rejected` 狀態時獲得新的入群題目

#### /answer
在 `filling` 狀態時設定答案，範例：
```
/answer
1. 答案一
2. 答案二...
```

#### /submit
在 `filling` 狀態時回答完問題後送出申請，管理群組會收到通知

#### /join
在 `approved` 狀態時取得入群連結

### Admin
#### /review
查看申請答案
* `/review 12345` - 查看12345的申請答案

#### /comment
設定給申請者的訊息，訊息會在 `/approve` 或 `/reject` 後同時發送給申請者，需要有 `review` 權限
* `/comment 12345 歡迎` - 給12345訊息「歡迎」

#### /approve
批准申請，需要有 `review` 權限
* `/approve 12345` - 批准12345的申請

#### /reject
拒絕申請，需要有 `review` 權限
* `/reject 12345` - 拒絕12345的申請

#### /ban
禁止申請，需要有 `review` 權限
* `/ban 12345` - 禁止12345的申請

#### /list_request
列出目前的申請

#### /grant_review
授予其他人審核權限，需要有 `grant` 權限

#### /revoke_review
撤銷其他人審核權限，需要有 `grant` 權限

#### /grant_grant
授予其他人授權權限，需要有 `super` 權限

#### /revoke_grant
撤銷其他人授權權限，需要有 `super` 權限

#### /set_status
設定申請狀態，僅在 Debug Mode 啟用時有效
* `/set_status 12345 new` 將12345的申請狀態設定為 `new`

#### /delete
刪除使用者，僅在 Debug Mode 啟用時有效
* `/delete 12345` 刪除使用者12345

## Status
| status | description |
| --- | --- |
| `new` | 新使用者 |
| `filling` | 正在回答入群問題 |
| `submitted` | 已送出申請 |
| `rejected` | 申請已被拒絕 |
| `banned` | 被禁止申請 |
| `approved` | 申請已被批准 |
| `joined` | 已加入群組 |

## Permission
| permission | description |
| --- | --- |
| `review` | 可進行審核 |
| `grant` | 可授予其他人審核權限 |
| `super` | 可授予其他人授權權限 |
