# エラーハンドリングポリシー

## 原則

**Fail-Fast原則**: 不正な入力または状態は即座に失敗処理を行う。サイレントな失敗は禁止。

エラーは早期に検出し、適切にログを記録し、ユーザーに意味のあるフィードバックを提供することで、デバッグを容易にし、システムの信頼性を向上させる。

---

## ルール

| ルール                   | 説明                                                        | 必須度  |
| ------------------------ | ----------------------------------------------------------- | :-----: |
| **Try-Catch + LogUtils** | すべての非同期処理は`try-catch` + `LogUtils`でエラーを記録  | ✅ MUST |
| **空のCatch禁止**        | `catch (e) {}`は禁止。エラーを無視してはならない            | ✅ MUST |
| **Fail-Fast**            | 不正な入力/状態は即座に失敗処理（アサーション、例外スロー） | ✅ MUST |
| **Riverpod AsyncValue**  | Notifier内では`AsyncValue.guard()`を使用                    | ✅ MUST |
| **UI Error Display**     | `AsyncValue.when()`でloading/data/error状態を処理           | ✅ MUST |
| **Edge Function Error**  | 構造化されたJSONエラーレスポンス（ステータスコード付き）    | ✅ MUST |
| **Domain Error Mapping** | PostgreSQLエラーをドメインエラーにマッピング                | ✅ MUST |

---

## パターン別ガイドライン

### 1. Riverpod Notifierでのエラーハンドリング

#### ✅ 正しいパターン

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../utils/log_utils.dart';

part 'user_notifier.g.dart';

@riverpod
class UserNotifier extends _$UserNotifier {
  @override
  FutureOr<User?> build() async {
    return await _loadUser();
  }

  Future<void> updateProfile(String name, String bio) async {
    state = const AsyncValue.loading();

    state = await AsyncValue.guard(() async {
      try {
        final user = await ref.read(userRepositoryProvider).updateProfile(
          name: name,
          bio: bio,
        );
        LogUtils.i(
          tag: 'UserNotifier',
          msg: 'Profile updated successfully: userId=${user.id}',
        );
        return user;
      } catch (e, st) {
        LogUtils.e(
          tag: 'UserNotifier',
          msg: 'Failed to update profile',
          error: e,
          stackTrace: st,
        );
        rethrow; // AsyncValue.guard()がエラーをキャッチ
      }
    });
  }

  Future<User?> _loadUser() async {
    try {
      final user = await ref.read(userRepositoryProvider).getCurrentUser();
      LogUtils.d(tag: 'UserNotifier', msg: 'User loaded: ${user?.id}');
      return user;
    } catch (e, st) {
      LogUtils.e(
        tag: 'UserNotifier',
        msg: 'Failed to load user',
        error: e,
        stackTrace: st,
      );
      return null; // buildメソッドではnullを返すことでエラー状態を示す
    }
  }
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: エラーを無視
@riverpod
class BadUserNotifier extends _$BadUserNotifier {
  @override
  FutureOr<User?> build() async {
    try {
      return await ref.read(userRepositoryProvider).getCurrentUser();
    } catch (e) {
      // ❌ エラーをログに記録せず無視
      return null;
    }
  }

  Future<void> updateProfile(String name, String bio) async {
    try {
      final user = await ref.read(userRepositoryProvider).updateProfile(
        name: name,
        bio: bio,
      );
      state = AsyncValue.data(user);
    } catch (e) {
      // ❌ print()を使用（LogUtils必須）
      print('Error: $e');
      // ❌ エラー状態を設定しない
    }
  }
}
```

---

### 2. UIでのエラー表示

#### ✅ 正しいパターン

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

class UserProfileScreen extends ConsumerWidget {
  const UserProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final userState = ref.watch(userNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.profile)),
      body: userState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) {
          // ✅ エラーをログに記録
          LogUtils.e(
            tag: 'UserProfileScreen',
            msg: 'Failed to load user profile',
            error: error,
            stackTrace: stackTrace,
          );

          // ✅ ユーザーに意味のあるメッセージを表示
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                Text(
                  l10n.errorLoadingProfile,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  error.toString(),
                  style: Theme.of(context).textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => ref.invalidate(userNotifierProvider),
                  child: Text(l10n.retry),
                ),
              ],
            ),
          );
        },
        data: (user) {
          if (user == null) {
            return Center(child: Text(l10n.userNotFound));
          }
          return _buildUserProfile(context, user);
        },
      ),
    );
  }

  Widget _buildUserProfile(BuildContext context, User user) {
    // プロフィール表示ロジック
    return ListView(
      children: [
        // ...
      ],
    );
  }
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: エラー状態を処理しない
class BadUserProfileScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(userNotifierProvider).value;

    // ❌ loading/errorを処理しない
    if (user == null) {
      return const Center(child: Text('No user'));
    }

    return _buildUserProfile(context, user);
  }
}
```

---

### 3. Repositoryでのエラーハンドリング

#### ✅ 正しいパターン

```dart
import 'package:supabase_flutter/supabase_flutter.dart';
import '../utils/log_utils.dart';

/// ユーザーリポジトリ
class UserRepository {
  final SupabaseClient _client;

  UserRepository(this._client);

  /// ユーザープロフィールを更新
  ///
  /// 不正なデータの場合は[ArgumentError]をスロー
  /// DB接続エラーの場合は[RepositoryException]をスロー
  Future<User> updateProfile({
    required String name,
    required String bio,
  }) async {
    // ✅ Fail-Fast: 不正な入力を即座にチェック
    if (name.trim().isEmpty) {
      throw ArgumentError('Name cannot be empty');
    }
    if (bio.length > 500) {
      throw ArgumentError('Bio must be less than 500 characters');
    }

    try {
      final userId = _client.auth.currentUser?.id;
      if (userId == null) {
        throw const RepositoryException(
          code: 'UNAUTHENTICATED',
          message: 'User not authenticated',
        );
      }

      final response = await _client
          .from('users')
          .update({
            'name': name,
            'bio': bio,
            'updated_at': DateTime.now().toIso8601String(),
          })
          .eq('id', userId)
          .select()
          .single();

      LogUtils.i(
        tag: 'UserRepository',
        msg: 'Profile updated: userId=$userId',
      );

      return User.fromJson(response);
    } on PostgrestException catch (e, st) {
      // ✅ PostgreSQLエラーをドメインエラーにマッピング
      LogUtils.e(
        tag: 'UserRepository',
        msg: 'PostgreSQL error during profile update',
        error: e,
        stackTrace: st,
      );
      throw RepositoryException(
        code: 'DB_ERROR',
        message: 'Failed to update profile: ${e.message}',
        originalError: e,
      );
    } catch (e, st) {
      LogUtils.e(
        tag: 'UserRepository',
        msg: 'Unexpected error during profile update',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}

/// リポジトリ例外
class RepositoryException implements Exception {
  final String code;
  final String message;
  final Object? originalError;

  const RepositoryException({
    required this.code,
    required this.message,
    this.originalError,
  });

  @override
  String toString() => 'RepositoryException($code): $message';
}
```

#### ❌ 誤ったパターン

```dart
// ❌ BAD: エラーハンドリングが不十分
class BadUserRepository {
  Future<User> updateProfile(String name, String bio) async {
    // ❌ 入力検証なし（Fail-Fast違反）

    try {
      final response = await _client
          .from('users')
          .update({'name': name, 'bio': bio})
          .select()
          .single();
      return User.fromJson(response);
    } catch (e) {
      // ❌ エラーをログに記録しない
      // ❌ エラーを具体的にマッピングしない
      return User.empty(); // ❌ サイレントな失敗
    }
  }
}
```

---

### 4. Edge Functionでのエラーハンドリング

#### ✅ 正しいパターン (TypeScript)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ✅ 構造化されたエラーレスポンス型
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

serve(async (req: Request) => {
  try {
    // ✅ Authorization検証
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      return new Response(
        JSON.stringify({
          error: {
            code: 'UNAUTHORIZED',
            message: 'Authorization header required',
          },
        } as ErrorResponse),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ✅ 入力検証（Fail-Fast）
    const body = await req.json();
    if (!body.userId || !body.content) {
      return new Response(
        JSON.stringify({
          error: {
            code: 'INVALID_INPUT',
            message: 'userId and content are required',
          },
        } as ErrorResponse),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ビジネスロジック
    const result = await processUserContent(body.userId, body.content);

    return new Response(JSON.stringify({ data: result }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    // ✅ エラーをログに記録
    console.error('Edge Function Error:', error);

    // ✅ 構造化されたエラーレスポンスを返す
    return new Response(
      JSON.stringify({
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
          details: error,
        },
      } as ErrorResponse),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
});
```

#### ❌ 誤ったパターン (TypeScript)

```typescript
// ❌ BAD: エラーハンドリングが不十分
serve(async (req: Request) => {
  // ❌ try-catchなし
  const body = await req.json();

  // ❌ 入力検証なし

  const result = await processUserContent(body.userId, body.content);

  // ❌ エラー時の処理がない
  return new Response(JSON.stringify(result));
});
```

---

## エラー分類とマッピング

| エラータイプ         | HTTPステータス | コード例                    | 処理方法                            |
| -------------------- | -------------- | --------------------------- | ----------------------------------- |
| **バリデーション**   | 400            | `INVALID_INPUT`             | Fail-Fast、即座に拒否               |
| **認証**             | 401            | `UNAUTHENTICATED`           | ログインページへリダイレクト        |
| **認可**             | 403            | `UNAUTHORIZED`              | アクセス拒否メッセージ表示          |
| **Not Found**        | 404            | `NOT_FOUND`                 | リソースが見つからない旨表示        |
| **ビジネスロジック** | 422            | `BUSINESS_RULE_VIOLATION`   | 具体的なルール違反メッセージ        |
| **DB/ネットワーク**  | 500            | `DB_ERROR`, `NETWORK_ERROR` | リトライオプション提供              |
| **予期しないエラー** | 500            | `INTERNAL_ERROR`            | 一般的なエラーメッセージ + ログ記録 |

---

## チェックリスト

実装時に以下を確認してください：

- [ ] すべての非同期処理に`try-catch`がある
- [ ] エラーは`LogUtils`でログ記録されている
- [ ] 空の`catch (e) {}`ブロックがない
- [ ] 不正な入力は即座にチェックされている（Fail-Fast）
- [ ] Riverpod Notifierで`AsyncValue.guard()`を使用
- [ ] UIで`AsyncValue.when()`を使用してerror状態を処理
- [ ] Edge Functionで構造化されたエラーJSONを返す
- [ ] PostgreSQLエラーはドメインエラーにマッピングされている
- [ ] ユーザーに意味のあるエラーメッセージを表示

---

## 参考資料

- [CLAUDE.md - エラーハンドリング](../../CLAUDE.md#必須ルールmust)
- [LogUtilsドキュメント](../technical/logging-utils.md)
- [Riverpodエラーハンドリング](../../docs/riverpod-docs/essentials/side_effects.md)
- [Edge Functionsベストプラクティス](../../infra/supabase/README.md)
