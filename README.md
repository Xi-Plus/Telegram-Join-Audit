# Telegram-Join-Audit

## FAQ
+ 未申請就入群的人在申請通過後會解 Ban ？
	+ <b>注意！</b>機器人會記錄是否曾封鎖過該申請人，若有，在管理員批准後即會嘗試解除封鎖該使用者，就算是後來其他管理員修改了封鎖也是如此，進行審核的管理員應自行注意此事，或者你可能想要使用 `/ban` 指令來禁止其申請
+ 機器人故障時入群的人，在機器人恢復後會如何處理？
	+ 不會有任何處理，入群時無論是否申請通過皆會有提示訊息，若沒有訊息就代表機器人故障了
+ 未申請通過的人被 Ban 前發送的訊息會如何處理？
	+ 不會有任何處理
+ 可以透過機器人和申請者對話？
	+ 無法，`/comment` 所設定的訊息僅會在 `/reanswer` 、 `/approve` 或 `/reject` 時一次性發送給申請者
+ 申請者可以將入群連結交給其他人使用？
	+ 無法，入群時會檢查是否通過申請，不會檢查入群連結是否屬於該申請者
+ 在機器人啟用前已在群組內的人可以申請入群嗎？
	+ 可以，你可能想要先將群員名單匯入資料庫來避免此事發生
+ 需要給予機器人什麼權限？
	+ 在受限群（`CENSORED`）給予機器人 `Ban users` 和 `Add users` 權限

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
設定給申請者的訊息，訊息會在 `reanswer` 、 `/approve` 或 `/reject` 後同時發送給申請者，需要有 `review` 權限
* `/comment 12345 歡迎` - 給12345訊息「歡迎」

#### /reanswer
要求申請者重新作答，需要有 `review` 權限
* `/reanswer 12345` - 要求12345重新作答

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
設定申請狀態，僅在 Debug Mode 啟用時有效，需要有 `review` 權限
* `/set_status 12345 new` 將12345的申請狀態設定為 `new`

#### /delete
刪除使用者，僅在 Debug Mode 啟用時有效，需要有 `review` 權限
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
