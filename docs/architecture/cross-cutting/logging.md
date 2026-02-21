# ロギングポリシー

## 原則

**すべてのログは`LogUtils`経由で記録する。`print()`の使用は禁止。**

構造化されたログは、デバッグ、モニタリング、トラブルシューティングを容易にし、本番環境での問題解決を迅速化する。

---

## ルール

| ルール             | 説明                                                              | 必須度  |
| ------------------ | ----------------------------------------------------------------- | :-----: |
| **LogUtils使用**   | すべてのログは`LogUtils`経由で記録                                | ✅ MUST |
| **print()禁止**    | `print()`の使用は禁止（`LogUtils`を使用）                         | ✅ MUST |
| **適切なレベル**   | エラー(e)、警告(w)、情報(i)、デバッグ(d)を適切に使い分ける        | ✅ MUST |
| **Tag指定**        | `tag`パラメータにクラス名またはモジュール名を指定                 | ✅ MUST |
| **PII除外**        | 個人情報、パスワード、APIキー、セッショントークンをログに含めない | ✅ MUST |
| **リリースビルド** | デバッグログはリリースビルドで自動的に削除される                  | ℹ️ INFO |

---

## ログレベル

### 1. Error (e) - エラー

**用途**: システムエラー、例外、失敗した操作

```dart
LogUtils.e(
  tag: 'UserRepository',
  msg: 'Failed to fetch user data',
  error: exception,
  stackTrace: stackTrace,
);
```

**記録すべき内容**:

- API呼び出しの失敗
- データベースエラー
- 認証/認可エラー
- 予期しない例外
- クラッシュの原因となる可能性のあるエラー

---

### 2. Warning (w) - 警告

**用途**: 潜在的な問題、回復可能なエラー、非推奨の使用

```dart
LogUtils.w(
  tag: 'CacheManager',
  msg: 'Cache miss for key: $cacheKey, falling back to network',
);
```

**記録すべき内容**:

- キャッシュミス
- フォールバック処理の実行
- 非推奨APIの使用
- リトライが必要な操作
- パフォーマンスの問題

---

### 3. Info (i) - 情報

**用途**: 重要なビジネスイベント、状態遷移

```dart
LogUtils.i(
  tag: 'AuthService',
  msg: 'User logged in successfully: userId=$userId',
);
```

**記録すべき内容**:

- ユーザー認証イベント（ログイン、ログアウト）
- 重要なビジネストランザクション
- 状態遷移（アクティブ、サスペンド、再開）
- Edge Function呼び出し
- サブスクリプション変更

---

### 4. Debug (d) - デバッグ

**用途**: 開発中のデバッグ情報、詳細なトレース

```dart
LogUtils.d(
  tag: 'CourseNotifier',
  msg: 'Loading courses: filter=$filter, limit=$limit',
);
```

**記録すべき内容**:

- 関数呼び出しのトレース
- 変数の値
- 条件分岐の結果
- ループの反復
- 開発中の一時的なログ

**注意**: デバッグログはリリースビルドで自動的に削除されます。

---

## パターン別ガイドライン

### 1. Repository層でのロギング

#### ✅ 正しいパターン

```dart
import '../utils/log_utils.dart';

class CourseRepository {
  final SupabaseClient _client;

  CourseRepository(this._client);

  /// コース一覧を取得
  Future<List<Course>> getCourses({
    required String userId,
    CourseFilter? filter,
  }) async {
    // ✅ デバッグログ: 入力パラメータ
    LogUtils.d(
      tag: 'CourseRepository',
      msg: 'Fetching courses: userId=$userId, filter=$filter',
    );

    try {
      final query = _client
          .from('courses')
          .select()
          .eq('user_id', userId);

      if (filter != null) {
        // フィルタ適用ロジック
      }

      final response = await query;

      // ✅ 情報ログ: 成功した操作
      LogUtils.i(
        tag: 'CourseRepository',
        msg: 'Fetched ${response.length} courses for user: $userId',
      );

      return response.map((json) => Course.fromJson(json)).toList();
    } on PostgrestException catch (e, st) {
      // ✅ エラーログ: 例外の詳細
      LogUtils.e(
        tag: 'CourseRepository',
        msg: 'PostgreSQL error while fetching courses',
        error: e,
        stackTrace: st,
      );
      rethrow;
    } catch (e, st) {
      // ✅ エラーログ: 予期しない例外
      LogUtils.e(
        tag: 'CourseRepository',
        msg: 'Unexpected error while fetching courses',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  /// コースを作成
  Future<Course> createCourse(CreateCourseDto dto) async {
    // ✅ 情報ログ: ビジネスイベント（PIIを除外）
    LogUtils.i(
      tag: 'CourseRepository',
      msg: 'Creating course: type=${dto.courseType}, level=${dto.level}',
      // ❌ BAD: userId=$userId, name=${dto.courseName} ← PIIを含めない
    );

    try {
      final response = await _client
          .from('courses')
          .insert(dto.toJson())
          .select()
          .single();

      // ✅ 情報ログ: 成功
      LogUtils.i(
        tag: 'CourseRepository',
        msg: 'Course created successfully: courseId=${response['id']}',
      );

      return Course.fromJson(response);
    } catch (e, st) {
      LogUtils.e(
        tag: 'CourseRepository',
        msg: 'Failed to create course',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}
```

#### ❌ 誤ったパターン

```dart
class BadCourseRepository {
  Future<List<Course>> getCourses(String userId) async {
    // ❌ BAD: print()を使用
    print('Fetching courses for user: $userId');

    try {
      final response = await _client
          .from('courses')
          .select()
          .eq('user_id', userId);

      // ❌ BAD: print()を使用
      print('Got ${response.length} courses');

      return response.map((json) => Course.fromJson(json)).toList();
    } catch (e) {
      // ❌ BAD: print()を使用、stackTraceなし
      print('Error: $e');
      rethrow;
    }
  }

  Future<Course> createCourse(CreateCourseDto dto) async {
    // ❌ BAD: PIIをログに含める
    print('Creating course: userId=${dto.userId}, email=${dto.userEmail}');

    try {
      final response = await _client
          .from('courses')
          .insert(dto.toJson())
          .select()
          .single();

      return Course.fromJson(response);
    } catch (e) {
      // ❌ BAD: エラーをログに記録しない
      return Course.empty();
    }
  }
}
```

---

### 2. Notifier層でのロギング

#### ✅ 正しいパターン

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../utils/log_utils.dart';

part 'course_notifier.g.dart';

@riverpod
class CourseNotifier extends _$CourseNotifier {
  @override
  FutureOr<List<Course>> build() async {
    // ✅ デバッグログ: 初期化
    LogUtils.d(tag: 'CourseNotifier', msg: 'Building CourseNotifier');

    return await _loadCourses();
  }

  Future<void> refreshCourses() async {
    // ✅ 情報ログ: ユーザーアクション
    LogUtils.i(tag: 'CourseNotifier', msg: 'User requested course refresh');

    state = const AsyncValue.loading();

    state = await AsyncValue.guard(() async {
      final courses = await _loadCourses();

      // ✅ 情報ログ: 成功
      LogUtils.i(
        tag: 'CourseNotifier',
        msg: 'Courses refreshed: count=${courses.length}',
      );

      return courses;
    });

    // エラーの場合、AsyncValue.guard()が自動的に処理
    state.whenOrNull(
      error: (error, stackTrace) {
        // ✅ エラーログ
        LogUtils.e(
          tag: 'CourseNotifier',
          msg: 'Failed to refresh courses',
          error: error,
          stackTrace: stackTrace,
        );
      },
    );
  }

  Future<void> createCourse(CreateCourseDto dto) async {
    // ✅ 情報ログ: ビジネスアクション
    LogUtils.i(
      tag: 'CourseNotifier',
      msg: 'Creating new course: type=${dto.courseType}',
    );

    try {
      final newCourse = await ref.read(courseRepositoryProvider).createCourse(dto);

      // 既存のコースリストに追加
      state.whenData((courses) {
        state = AsyncValue.data([...courses, newCourse]);
      });

      // ✅ 情報ログ: 成功
      LogUtils.i(
        tag: 'CourseNotifier',
        msg: 'Course created: courseId=${newCourse.id}',
      );
    } catch (e, st) {
      // ✅ エラーログ
      LogUtils.e(
        tag: 'CourseNotifier',
        msg: 'Failed to create course',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  Future<List<Course>> _loadCourses() async {
    try {
      final userId = ref.read(authServiceProvider).currentUser?.id;
      if (userId == null) {
        // ✅ 警告ログ: ユーザー未認証
        LogUtils.w(
          tag: 'CourseNotifier',
          msg: 'Cannot load courses: user not authenticated',
        );
        return [];
      }

      final courses = await ref.read(courseRepositoryProvider).getCourses(
        userId: userId,
      );

      return courses;
    } catch (e, st) {
      LogUtils.e(
        tag: 'CourseNotifier',
        msg: 'Failed to load courses',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}
```

---

### 3. Service層でのロギング

#### ✅ 正しいパターン

```dart
class TtsService {
  final SupabaseClient _client;

  TtsService(this._client);

  /// テキストを音声に変換
  Future<String> textToSpeech({
    required String text,
    required String languageCode,
    String? voiceName,
  }) async {
    // ✅ デバッグログ: パラメータ（PIIを除外）
    LogUtils.d(
      tag: 'TtsService',
      msg: 'TTS request: lang=$languageCode, voice=$voiceName, textLength=${text.length}',
    );

    try {
      // ✅ 情報ログ: Edge Function呼び出し
      LogUtils.i(
        tag: 'TtsService',
        msg: 'Calling cloud-tts Edge Function',
      );

      final response = await _client.functions.invoke(
        'cloud-tts',
        body: {
          'text': text,
          'languageCode': languageCode,
          'voiceName': voiceName,
        },
      );

      if (response.status != 200) {
        // ✅ エラーログ: Edge Functionエラー
        LogUtils.e(
          tag: 'TtsService',
          msg: 'TTS Edge Function failed: status=${response.status}',
          error: response.data,
        );
        throw TtsException('TTS request failed: ${response.data}');
      }

      final audioUrl = response.data['audioUrl'] as String;

      // ✅ 情報ログ: 成功
      LogUtils.i(
        tag: 'TtsService',
        msg: 'TTS completed: audioUrl length=${audioUrl.length}',
      );

      return audioUrl;
    } on FunctionException catch (e, st) {
      // ✅ エラーログ: 例外詳細
      LogUtils.e(
        tag: 'TtsService',
        msg: 'TTS FunctionException',
        error: e,
        stackTrace: st,
      );
      rethrow;
    } catch (e, st) {
      LogUtils.e(
        tag: 'TtsService',
        msg: 'Unexpected TTS error',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}
```

---

### 4. Edge Functionでのロギング (TypeScript)

#### ✅ 正しいパターン

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

serve(async (req: Request) => {
  // ✅ 情報ログ: リクエスト受信
  console.log('[cloud-tts] Request received:', {
    method: req.method,
    url: req.url,
    timestamp: new Date().toISOString(),
  });

  try {
    const { text, languageCode, voiceName } = await req.json();

    // ✅ デバッグログ: パラメータ（PIIを除外）
    console.log('[cloud-tts] Parameters:', {
      languageCode,
      voiceName,
      textLength: text.length,
      // ❌ text: text ← テキスト内容はPIIの可能性があるため除外
    });

    // ✅ 情報ログ: 外部API呼び出し
    console.log('[cloud-tts] Calling Google Cloud TTS API');

    const ttsResult = await callGoogleTtsApi(text, languageCode, voiceName);

    // ✅ 情報ログ: 成功
    console.log('[cloud-tts] TTS completed successfully:', {
      audioSize: ttsResult.audio.length,
      duration: ttsResult.duration,
    });

    return new Response(JSON.stringify({ audioUrl: ttsResult.audioUrl }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    // ✅ エラーログ: 構造化されたエラー情報
    console.error('[cloud-tts] Error:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
      timestamp: new Date().toISOString(),
    });

    return new Response(
      JSON.stringify({
        error: {
          code: 'TTS_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
        },
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
});
```

#### ❌ 誤ったパターン (TypeScript)

```typescript
// ❌ BAD: ログなし、PIIを記録
serve(async (req: Request) => {
  try {
    const { text, languageCode } = await req.json();

    // ❌ BAD: PIIをログに記録
    console.log('TTS request:', text);

    const result = await callGoogleTtsApi(text, languageCode);

    return new Response(JSON.stringify(result));
  } catch (error) {
    // ❌ BAD: エラーをログに記録しない
    return new Response(JSON.stringify({ error: 'Failed' }));
  }
});
```

---

## ログに含めてはいけない情報（PII除外）

| 情報タイプ             | 例                               | 代替                       |
| ---------------------- | -------------------------------- | -------------------------- |
| **個人情報**           | メールアドレス、電話番号、住所   | userId, userType           |
| **認証情報**           | パスワード、APIキー、トークン    | `"[REDACTED]"`             |
| **セッション**         | セッショントークン、Cookie       | セッションID（ハッシュ化） |
| **ユーザーコンテンツ** | チャットメッセージ、学習テキスト | 文字数、言語コード         |
| **決済情報**           | クレジットカード番号             | 決済IDのみ                 |

### ✅ 正しい例

```dart
// ✅ PII除外
LogUtils.i(
  tag: 'AuthService',
  msg: 'User logged in: userId=$userId, method=google',
);

// ✅ 集計データのみ
LogUtils.i(
  tag: 'ChatService',
  msg: 'Message sent: messageLength=${message.length}, languageCode=$lang',
);

// ✅ ハッシュ化
LogUtils.d(
  tag: 'SessionManager',
  msg: 'Session created: sessionHash=${sessionId.hashCode}',
);
```

### ❌ 誤った例

```dart
// ❌ PIIをログに含める
LogUtils.i(
  tag: 'AuthService',
  msg: 'User logged in: email=${user.email}, name=${user.name}',
);

// ❌ ユーザーコンテンツをログに含める
LogUtils.i(
  tag: 'ChatService',
  msg: 'Message sent: text="${message.text}"',
);

// ❌ 認証情報をログに含める
LogUtils.d(
  tag: 'ApiClient',
  msg: 'Request sent: apiKey=$apiKey, token=$token',
);
```

---

## リリースビルドでのログ動作

### デバッグログの自動削除

リリースビルドでは、`LogUtils.d()`によるデバッグログは自動的に削除されます。

```dart
// LogUtils実装例（参考）
class LogUtils {
  static void d({required String tag, required String msg}) {
    // kDebugModeはリリースビルドでfalse
    if (kDebugMode) {
      developer.log(msg, name: tag, level: 500);
    }
  }

  static void i({required String tag, required String msg}) {
    // 情報ログはリリースビルドでも記録
    developer.log(msg, name: tag, level: 800);
  }

  static void e({
    required String tag,
    required String msg,
    Object? error,
    StackTrace? stackTrace,
  }) {
    // エラーログはリリースビルドでも記録
    developer.log(
      msg,
      name: tag,
      level: 1000,
      error: error,
      stackTrace: stackTrace,
    );
  }
}
```

---

## チェックリスト

実装時に以下を確認してください：

- [ ] すべてのログは`LogUtils`経由で記録されている
- [ ] `print()`を使用していない
- [ ] 適切なログレベル（e/w/i/d）を使用している
- [ ] `tag`パラメータにクラス名を指定している
- [ ] PIIをログに含めていない（メール、パスワード、トークン等）
- [ ] エラーログに`error`と`stackTrace`を含めている
- [ ] 重要なビジネスイベントを情報ログで記録している
- [ ] デバッグログ(`d`)は開発中の一時的な情報のみ

---

## 参考資料

- [CLAUDE.md - ロギングルール](../../CLAUDE.md#必須ルールmust)
- [エラーハンドリングポリシー](./error-handling.md)
- [セキュリティポリシー - PII保護](./security.md)
