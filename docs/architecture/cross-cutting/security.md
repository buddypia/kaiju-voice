# セキュリティポリシー

## 原則

**セキュリティはシステム設計の中核要素であり、後付けの対策ではない。**

すべての層（クライアント、Edge Function、データベース）で多層防御を実装し、ゼロトラストの原則に基づいてアクセス制御を行う。

---

## ルール

| ルール                     | 説明                                                           | 必須度  |
| -------------------------- | -------------------------------------------------------------- | :-----: |
| **Supabase Auth**          | 認証はSupabase Auth + Google Sign-In                           | ✅ MUST |
| **RLS必須**                | すべてのテーブルにRow Level Security (RLS)ポリシーを設定       | ✅ MUST |
| **service_role禁止**       | `service_role`キーをクライアントに露出しない                   | ✅ MUST |
| **Authorization検証**      | Edge FunctionでAuthorizationヘッダーを検証                     | ✅ MUST |
| **入力サニタイゼーション** | すべてのユーザー入力をサニタイズ                               | ✅ MUST |
| **AI API制限**             | Gemini API呼び出しはEdge Functionのみ（クライアント禁止）      | ✅ MUST |
| **responseSchema強制**     | AI応答は`responseSchema`で構造化（自由テキスト禁止）           | ✅ MUST |
| **環境変数管理**           | シークレットは環境変数（.env.local, .env.production、git除外） | ✅ MUST |
| **PII保護**                | 個人情報をログに記録しない                                     | ✅ MUST |
| **依存関係監査**           | 定期的な依存関係のセキュリティ監査                             | ✅ MUST |

---

## 1. 認証・認可

### 1.1 Supabase Auth + Google Sign-In

**原則**: すべての認証はSupabase Authを通じて行う。カスタム認証ロジックは禁止。

#### ✅ 正しいパターン

```dart
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  final SupabaseClient _client;

  AuthService(this._client);

  /// Googleでログイン
  Future<User?> signInWithGoogle() async {
    try {
      // ✅ Google Sign-In
      final googleSignIn = GoogleSignIn(
        clientId: '[YOUR_CLIENT_ID]',
        serverClientId: '[YOUR_SERVER_CLIENT_ID]',
      );

      final googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        LogUtils.w(tag: 'AuthService', msg: 'Google sign-in cancelled by user');
        return null;
      }

      final googleAuth = await googleUser.authentication;

      // ✅ Supabase Authで認証
      final response = await _client.auth.signInWithIdToken(
        provider: OAuthProvider.google,
        idToken: googleAuth.idToken!,
        accessToken: googleAuth.accessToken,
      );

      LogUtils.i(
        tag: 'AuthService',
        msg: 'User signed in: userId=${response.user?.id}',
      );

      return response.user;
    } catch (e, st) {
      LogUtils.e(
        tag: 'AuthService',
        msg: 'Failed to sign in with Google',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  /// ログアウト
  Future<void> signOut() async {
    try {
      await _client.auth.signOut();
      LogUtils.i(tag: 'AuthService', msg: 'User signed out');
    } catch (e, st) {
      LogUtils.e(
        tag: 'AuthService',
        msg: 'Failed to sign out',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  /// 現在のユーザー取得
  User? get currentUser => _client.auth.currentUser;

  /// 認証状態のストリーム
  Stream<AuthState> get authStateChanges => _client.auth.onAuthStateChange;
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: カスタム認証ロジック
class BadAuthService {
  Future<User?> signIn(String email, String password) async {
    // ❌ 独自の認証ロジック（Supabase Authを使用すべき）
    final hashedPassword = _hashPassword(password);
    final user = await _db.query('SELECT * FROM users WHERE email = ? AND password = ?',
                                  [email, hashedPassword]);

    // ❌ セキュリティリスク: SQLインジェクション、弱いハッシュ化など
    return user;
  }
}
```

---

### 1.2 Edge FunctionでのAuthorization検証

**原則**: すべてのEdge FunctionでAuthorizationヘッダーを検証する。

#### ✅ 正しいパターン (TypeScript)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req: Request) => {
  try {
    // ✅ Authorizationヘッダーの検証
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      console.error('[ai-tutor-chat] Missing Authorization header');
      return new Response(
        JSON.stringify({
          error: {
            code: 'UNAUTHORIZED',
            message: 'Authorization header is required',
          },
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ✅ Supabaseクライアントを作成（anonキーでRLS有効）
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      {
        global: {
          headers: { Authorization: authHeader },
        },
      },
    );

    // ✅ ユーザー認証確認
    const {
      data: { user },
      error: authError,
    } = await supabaseClient.auth.getUser();

    if (authError || !user) {
      console.error('[ai-tutor-chat] Invalid auth token:', authError);
      return new Response(
        JSON.stringify({
          error: {
            code: 'UNAUTHORIZED',
            message: 'Invalid authentication token',
          },
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    console.log('[ai-tutor-chat] Authenticated user:', user.id);

    // ✅ ビジネスロジック（認証済みユーザーのみ）
    const body = await req.json();
    const result = await processAiTutorChat(user.id, body);

    return new Response(JSON.stringify({ data: result }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[ai-tutor-chat] Error:', error);
    return new Response(
      JSON.stringify({
        error: {
          code: 'INTERNAL_ERROR',
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
// ❌ BAD: Authorization検証なし
serve(async (req: Request) => {
  // ❌ 認証チェックなし
  const body = await req.json();
  const result = await processAiTutorChat(body.userId, body);

  return new Response(JSON.stringify(result));
});
```

---

## 2. Row Level Security (RLS)

### 2.1 RLSポリシー必須

**原則**: すべてのテーブルでRLSを有効化し、適切なポリシーを設定する。`service_role`キーはクライアントに露出しない。

#### ✅ 正しいパターン (SQL)

```sql
-- ✅ RLSを有効化
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

-- ✅ SELECTポリシー: ユーザーは自分のコースのみ閲覧可能
CREATE POLICY "Users can view their own courses"
  ON courses
  FOR SELECT
  USING (auth.uid() = user_id);

-- ✅ INSERTポリシー: ユーザーは自分のコースのみ作成可能
CREATE POLICY "Users can insert their own courses"
  ON courses
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ✅ UPDATEポリシー: ユーザーは自分のコースのみ更新可能
CREATE POLICY "Users can update their own courses"
  ON courses
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ✅ DELETE ポリシー: ユーザーは自分のコースのみ削除可能
CREATE POLICY "Users can delete their own courses"
  ON courses
  FOR DELETE
  USING (auth.uid() = user_id);
```

#### 複雑なRLSポリシー例

```sql
-- ✅ 複数条件のRLSポリシー
CREATE POLICY "Users can view published courses or their own drafts"
  ON courses
  FOR SELECT
  USING (
    -- 公開されたコース、または
    status = 'published'
    OR
    -- 自分の下書き
    (auth.uid() = user_id AND status = 'draft')
  );

-- ✅ 関連テーブルを参照するRLSポリシー
CREATE POLICY "Users can view lessons of their courses"
  ON lessons
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM courses
      WHERE courses.id = lessons.course_id
      AND courses.user_id = auth.uid()
    )
  );
```

#### ❌ 誤ったパターン (SQL)

```sql
-- ❌ BAD: RLS無効（すべてのユーザーがすべてのデータにアクセス可能）
ALTER TABLE courses DISABLE ROW LEVEL SECURITY;

-- ❌ BAD: ポリシーなし（RLSが有効でもポリシーがないとアクセス不可）
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
-- ポリシーなし

-- ❌ BAD: 過度に緩いポリシー
CREATE POLICY "Allow all access"
  ON courses
  FOR ALL
  USING (true);  -- すべてのユーザーにすべての操作を許可
```

### 2.2 service_role キーの取り扱い

**原則**: `service_role`キーは絶対にクライアントに露出しない。Edge Functionでのみ使用。

#### ✅ 正しいパターン

```typescript
// ✅ Edge Function内でのみservice_roleキーを使用
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req: Request) => {
  // ✅ service_roleキーは環境変数から取得（Edge Function内のみ）
  const supabaseAdmin = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '', // ✅ RLSをバイパス
  );

  // 管理者操作（例: すべてのユーザーのデータ集計）
  const { data, error } = await supabaseAdmin.from('users').select('*');

  // ...
});
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: クライアントアプリでservice_roleキーを使用
final supabase = SupabaseClient(
  'https://lwbmgbapiqsrlixtogqu.supabase.co',
  'service_role_key_here',  // ❌ 絶対にNG！
);
```

```typescript
// ❌ BAD: クライアント側JavaScriptでservice_roleキーを使用
const supabase = createClient(
  'https://lwbmgbapiqsrlixtogqu.supabase.co',
  'service_role_key_here', // ❌ 絶対にNG！
);
```

---

## 3. 入力サニタイゼーション

### 3.1 クライアント側の入力検証

**原則**: すべてのユーザー入力を検証し、サニタイズする。

#### ✅ 正しいパターン

```dart
import 'package:flutter/material.dart';

class CreateCourseForm extends StatefulWidget {
  @override
  State<CreateCourseForm> createState() => _CreateCourseFormState();
}

class _CreateCourseFormState extends State<CreateCourseForm> {
  final _formKey = GlobalKey<FormState>();
  final _courseNameController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        children: [
          TextFormField(
            controller: _courseNameController,
            decoration: InputDecoration(labelText: 'コース名'),
            // ✅ 入力検証
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'コース名を入力してください';
              }
              if (value.length > 100) {
                return 'コース名は100文字以内で入力してください';
              }
              // ✅ 危険な文字をチェック
              if (value.contains(RegExp(r'[<>\"\'`]'))) {
                return 'コース名に使用できない文字が含まれています';
              }
              return null;
            },
          ),
          ElevatedButton(
            onPressed: () {
              if (_formKey.currentState!.validate()) {
                // ✅ サニタイズされた入力を使用
                final sanitizedName = _courseNameController.text.trim();
                _createCourse(sanitizedName);
              }
            },
            child: Text('作成'),
          ),
        ],
      ),
    );
  }

  Future<void> _createCourse(String courseName) async {
    try {
      await ref.read(courseNotifierProvider.notifier).createCourse(
        CreateCourseDto(
          courseName: courseName,
          // ...
        ),
      );
    } catch (e, st) {
      LogUtils.e(
        tag: 'CreateCourseForm',
        msg: 'Failed to create course',
        error: e,
        stackTrace: st,
      );
      // エラー表示
    }
  }
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: 入力検証なし
class BadCreateCourseForm extends StatelessWidget {
  final _courseNameController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TextField(
          controller: _courseNameController,
          // ❌ バリデーションなし
        ),
        ElevatedButton(
          onPressed: () {
            // ❌ 生の入力をそのまま使用
            _createCourse(_courseNameController.text);
          },
          child: Text('作成'),
        ),
      ],
    );
  }
}
```

---

### 3.2 Edge Functionでの入力検証

#### ✅ 正しいパターン (TypeScript)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

serve(async (req: Request) => {
  try {
    const body = await req.json();

    // ✅ 必須フィールドの検証
    if (!body.userId || typeof body.userId !== 'string') {
      return new Response(
        JSON.stringify({
          error: {
            code: 'INVALID_INPUT',
            message: 'userId is required and must be a string',
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ✅ 文字列長の検証
    if (body.courseName && body.courseName.length > 100) {
      return new Response(
        JSON.stringify({
          error: {
            code: 'INVALID_INPUT',
            message: 'courseName must be less than 100 characters',
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ✅ 列挙型の検証
    const validStatuses = ['draft', 'published', 'archived'];
    if (body.status && !validStatuses.includes(body.status)) {
      return new Response(
        JSON.stringify({
          error: {
            code: 'INVALID_INPUT',
            message: `status must be one of: ${validStatuses.join(', ')}`,
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ✅ サニタイズ
    const sanitizedCourseName = body.courseName.trim();

    // ビジネスロジック
    const result = await createCourse({
      userId: body.userId,
      courseName: sanitizedCourseName,
      status: body.status,
    });

    return new Response(JSON.stringify({ data: result }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[create-course] Error:', error);
    return new Response(
      JSON.stringify({
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
        },
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
});
```

---

## 4. AI APIセキュリティ

### 4.1 Gemini API呼び出し制限

**原則**: Gemini API呼び出しはEdge Functionのみ。クライアントから直接呼び出しは禁止。

#### ✅ 正しいパターン

```typescript
// ✅ Edge Function内でGemini APIを呼び出し
import { GoogleGenerativeAI } from 'https://esm.sh/@google/generative-ai@0.1.1';

serve(async (req: Request) => {
  // Authorization検証（省略）

  try {
    const body = await req.json();

    // ✅ Gemini API keyは環境変数から取得
    const genAI = new GoogleGenerativeAI(Deno.env.get('GEMINI_API_KEY') ?? '');

    const model = genAI.getGenerativeModel({
      model: 'gemini-1.5-pro',
      generationConfig: {
        // ✅ CRITICAL: responseSchemaで構造化出力を強制
        responseMimeType: 'application/json',
        responseSchema: {
          type: 'object',
          properties: {
            content: { type: 'string' },
            suggestions: {
              type: 'array',
              items: { type: 'string' },
            },
            confidence: { type: 'number' },
          },
          required: ['content', 'suggestions', 'confidence'],
        },
      },
    });

    const prompt = `Generate educational content: ${body.topic}`;
    const result = await model.generateContent(prompt);
    const response = result.response.text();

    // ✅ JSONとしてパース（responseSchemaにより保証される）
    const parsedResponse = JSON.parse(response);

    console.log('[generate-content] AI response generated');

    return new Response(JSON.stringify({ data: parsedResponse }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[generate-content] Error:', error);
    return new Response(
      JSON.stringify({
        error: {
          code: 'AI_ERROR',
          message: error instanceof Error ? error.message : 'AI generation failed',
        },
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
});
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: クライアントから直接Gemini APIを呼び出し
class BadAiService {
  Future<String> generateContent(String topic) async {
    // ❌ APIキーがクライアントに露出
    final genAI = GoogleGenerativeAI('GEMINI_API_KEY_HERE');

    final model = genAI.getGenerativeModel(model: 'gemini-1.5-pro');
    final result = await model.generateContent(topic);

    return result.text;
  }
}
```

```typescript
// ❌ BAD: responseSchema未指定（自由テキスト応答）
const model = genAI.getGenerativeModel({
  model: 'gemini-1.5-pro',
  // ❌ responseSchemaなし → 構造化されていない応答
});

const result = await model.generateContent(prompt);
const response = result.response.text(); // ❌ 任意の形式のテキスト
```

---

### 4.2 responseSchema強制

**原則**: AI応答は必ず`responseSchema`で構造化する。自由テキスト応答は禁止。

#### ✅ 正しいパターン

```typescript
// ✅ 明確なスキーマ定義
const courseGenerationSchema = {
  type: 'object',
  properties: {
    courseName: {
      type: 'string',
      description: 'The name of the generated course',
    },
    description: {
      type: 'string',
      description: 'A brief description of the course',
    },
    lessons: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          content: { type: 'string' },
          duration: { type: 'number' },
        },
        required: ['title', 'content', 'duration'],
      },
    },
    difficulty: {
      type: 'string',
      enum: ['beginner', 'intermediate', 'advanced'],
    },
  },
  required: ['courseName', 'description', 'lessons', 'difficulty'],
};

const model = genAI.getGenerativeModel({
  model: 'gemini-1.5-pro',
  generationConfig: {
    responseMimeType: 'application/json',
    responseSchema: courseGenerationSchema,
  },
});
```

---

## 5. 環境変数とシークレット管理

### 5.1 環境変数ファイル

**原則**: シークレットは環境変数ファイルで管理し、gitにコミットしない。

#### ディレクトリ構造

```
hackathon-project/
├── .env.local          # ローカル開発用（git除外）
├── .env.production     # 本番環境用（git除外）
├── .env.example        # テンプレート（gitにコミット）
└── .gitignore          # .env.local, .env.productionを除外
```

#### ✅ .env.example（テンプレート）

```bash
# Supabase
SUPABASE_URL=https://lwbmgbapiqsrlixtogqu.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here  # Edge Functionのみ

# Google
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id_here
GOOGLE_OAUTH_SERVER_CLIENT_ID=your_google_server_client_id_here

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# RevenueCat
REVENUECAT_API_KEY=your_revenuecat_api_key_here

# Google Cloud TTS
GOOGLE_CLOUD_PROJECT_ID=your_project_id_here
GOOGLE_CLOUD_TTS_API_KEY=your_tts_api_key_here
```

#### ✅ .gitignore

```gitignore
# 環境変数ファイル
.env.local
.env.production

# その他のシークレット
*.key
*.pem
credentials.json
service-account.json
```

---

### 5.2 環境変数の読み込み

#### ✅ 正しいパターン (Dart)

```dart
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ✅ 環境変数を読み込み
  await dotenv.load(fileName: '.env.local');

  // ✅ 環境変数から取得
  final supabaseUrl = dotenv.env['SUPABASE_URL']!;
  final supabaseAnonKey = dotenv.env['SUPABASE_ANON_KEY']!;

  await Supabase.initialize(
    url: supabaseUrl,
    anonKey: supabaseAnonKey,  // ✅ anonキーのみ使用（RLS有効）
  );

  runApp(const MyApp());
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: APIキーのハードコーディング
await Supabase.initialize(
  url: 'https://lwbmgbapiqsrlixtogqu.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',  // ❌ ハードコーディング
);
```

---

## 6. データ保護

### 6.1 PII保護

**原則**: 個人情報（PII）をログに記録しない。

詳細は[ロギングポリシー - PII除外](./logging.md#ログに含めてはいけない情報pii除外)を参照。

### 6.2 暗号化

| データタイプ   | 暗号化方法     | 責任                  |
| -------------- | -------------- | --------------------- |
| **通信**       | HTTPS/TLS 1.2+ | Supabase              |
| **保存データ** | AES-256        | Supabase (PostgreSQL) |
| **トークン**   | JWT            | Supabase Auth         |
| **APIキー**    | 環境変数       | 開発者                |

---

## 7. 依存関係セキュリティ

### 7.1 依存関係監査

**原則**: 定期的に依存関係のセキュリティ脆弱性を監査する。

#### ✅ 定期監査コマンド

```bash
# Dart/Flutterパッケージの監査
flutter pub outdated

# npm/Denoパッケージの監査
npm audit

# 脆弱性のあるパッケージを更新
flutter pub upgrade
npm update
```

### 7.2 依存関係オーバーライド

**原則**: セキュリティ上の理由でオーバーライドする場合は、必ず文書化する。

#### ✅ 正しいパターン (pubspec.yaml)

```yaml
dependency_overrides:
  # ✅ Dart 3.8+ hashValues互換性問題
  # Issue: https://github.com/2d-inc/Flare-Flutter/issues/123
  # 解決策: hashValuesを削除したフォーク版を使用
  flare_flutter:
    git:
      url: https://github.com/mbfakourii/Flare-Flutter.git
      ref: remove_hashValues
```

#### 文書化場所

- `pubspec.yaml`にコメント
- [CLAUDE.md - 特殊設定](../../CLAUDE.md#特殊設定)
- 該当する技術文書

---

## 8. プラットフォームセキュリティ

### 8.1 プラットフォーム最小バージョン

| プラットフォーム | 最小バージョン        | 理由                                |
| ---------------- | --------------------- | ----------------------------------- |
| **iOS**          | 12.0                  | セキュリティアップデート、API互換性 |
| **Android**      | API 21 (Lollipop 5.0) | セキュリティパッチ、TLS 1.2サポート |

### 8.2 権限管理

#### ✅ 正しいパターン (AndroidManifest.xml)

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <application>
    <!-- ✅ 必要最小限の権限のみ -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />

    <!-- ✅ クリアテキスト通信を禁止 -->
    android:usesCleartextTraffic="false"

    <!-- ✅ バックアップを暗号化 -->
    android:allowBackup="true"
    android:fullBackupContent="@xml/backup_rules"
  </application>
</manifest>
```

#### ✅ 正しいパターン (Info.plist - iOS)

```xml
<dict>
  <!-- ✅ ATSを有効化（HTTP禁止） -->
  <key>NSAppTransportSecurity</key>
  <dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
  </dict>

  <!-- ✅ マイク使用の説明 -->
  <key>NSMicrophoneUsageDescription</key>
  <string>音声学習機能でマイクを使用します</string>
</dict>
```

---

## 9. CORS設定 (Edge Functions)

### ✅ 正しいパターン (TypeScript)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

serve(async (req: Request) => {
  // ✅ CORSヘッダー
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*', // または特定のドメイン
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
  };

  // ✅ OPTIONSリクエスト（プリフライト）
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: corsHeaders,
    });
  }

  try {
    // ビジネスロジック
    const result = await processRequest(req);

    return new Response(JSON.stringify({ data: result }), {
      status: 200,
      headers: {
        ...corsHeaders, // ✅ CORSヘッダーを含める
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        ...corsHeaders, // ✅ エラー時もCORSヘッダーを含める
        'Content-Type': 'application/json',
      },
    });
  }
});
```

---

## セキュリティチェックリスト

実装時に以下を確認してください：

### 認証・認可

- [ ] Supabase Auth + Google Sign-Inを使用
- [ ] Edge FunctionでAuthorizationヘッダーを検証
- [ ] カスタム認証ロジックは使用していない

### データベース

- [ ] すべてのテーブルでRLSを有効化
- [ ] 適切なRLSポリシーを設定
- [ ] `service_role`キーをクライアントに露出していない

### 入力検証

- [ ] すべてのユーザー入力を検証
- [ ] クライアント側とサーバー側の両方で検証
- [ ] 危険な文字をサニタイズ

### AI API

- [ ] Gemini API呼び出しはEdge Functionのみ
- [ ] `responseSchema`で構造化出力を強制
- [ ] AIキーをクライアントに露出していない

### 環境変数

- [ ] シークレットは環境変数で管理
- [ ] .env.local, .env.productionはgit除外
- [ ] ハードコーディングされたAPIキーなし

### ロギング

- [ ] PIIをログに含めていない
- [ ] パスワード、トークンをログに含めていない
- [ ] `LogUtils`を使用（`print()`禁止）

### 依存関係

- [ ] 定期的なセキュリティ監査
- [ ] 脆弱性のあるパッケージを更新
- [ ] オーバーライドは文書化

### プラットフォーム

- [ ] iOS 12.0+、Android API 21+
- [ ] 必要最小限の権限のみ
- [ ] HTTPS/TLS強制（HTTP禁止）

---

## 参考資料

- [CLAUDE.md - セキュリティルール](../../CLAUDE.md#必須ルールmust)
- [エラーハンドリングポリシー](./error-handling.md)
- [ロギングポリシー - PII保護](./logging.md)
- [Supabase RLSドキュメント](https://supabase.com/docs/guides/auth/row-level-security)
- [Postgresベストプラクティス](../../docs/supabase-overview.md#postgresベストプラクティスmust)
