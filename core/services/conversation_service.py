import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from core.config import Config
import pytz

class ConversationService:
    """
    Service quản lý lịch sử conversation với AI Agent.
    """
    
    def __init__(self, db_path: str = 'database/schedule.db', max_history: int = None):
        self.db_path = db_path
        self.max_history = max_history or Config.MAX_CONVERSATION_HISTORY
        self.vietnam_tz = pytz.timezone(Config.TIMEZONE)
        self._create_table()
    
    def _create_table(self):
        """Tạo bảng conversation_history nếu chưa tồn tại."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT 'default',
                role TEXT NOT NULL,  -- 'user' hoặc 'assistant'
                content TEXT NOT NULL,
                function_call TEXT,  -- JSON string của function call (nếu có)
                function_response TEXT,  -- JSON string của function response (nếu có)
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversation_session_timestamp 
            ON conversation_history(session_id, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user_message(self, content: str, session_id: str = 'default') -> int:
        """Thêm tin nhắn của user vào lịch sử."""
        return self._add_message(
            session_id=session_id,
            role='user',
            content=content
        )
    
    def add_assistant_message(self, content: str, function_call: Dict = None, 
                            function_response: Dict = None, session_id: str = 'default') -> int:
        """Thêm tin nhắn của assistant vào lịch sử."""
        return self._add_message(
            session_id=session_id,
            role='assistant',
            content=content,
            function_call=function_call,
            function_response=function_response
        )
    
    def _safe_json_serialize(self, obj) -> str:
        """Serialize object thành JSON an toàn, xử lý các kiểu phức tạp."""
        if obj is None:
            return None
        
        try:
            # Thử serialize trực tiếp trước
            return json.dumps(obj)
        except (TypeError, ValueError):
            try:
                # Nếu trực tiếp thất bại, chuyển thành dict trước
                if hasattr(obj, '__dict__'):
                    return json.dumps(obj.__dict__)
                elif hasattr(obj, '_asdict'):  # namedtuple
                    return json.dumps(obj._asdict())
                else:
                    # Fallback: chuyển thành chuỗi
                    return json.dumps(str(obj))
            except Exception as e:
                return json.dumps({"error": "serialization_failed", "type": str(type(obj))})

    def _add_message(self, session_id: str, role: str, content: str, 
                    function_call: Dict = None, function_response: Dict = None) -> int:
        """Thêm message vào database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(self.vietnam_tz)
        timestamp = now.isoformat()
        created_at = now.strftime('%Y-%m-%d %H:%M:%S')
        
        function_call_json = self._safe_json_serialize(function_call)
        function_response_json = self._safe_json_serialize(function_response)
        
        cursor.execute('''
            INSERT INTO conversation_history 
            (session_id, role, content, function_call, function_response, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, role, content, function_call_json, function_response_json, timestamp, created_at))
        
        message_id = cursor.lastrowid
        conn.commit()
        
        self._cleanup_old_messages(session_id, conn)
        
        conn.close()
        return message_id
    
    def _cleanup_old_messages(self, session_id: str, conn: sqlite3.Connection):
        """Xóa các message cũ để giữ trong giới hạn max_history."""
        cursor = conn.cursor()
        
        # Đếm số lượng message hiện tại
        cursor.execute('''
            SELECT COUNT(*) FROM conversation_history WHERE session_id = ?
        ''', (session_id,))
        
        count = cursor.fetchone()[0]
        
        if count > self.max_history:
            cursor.execute('''
                DELETE FROM conversation_history 
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM conversation_history 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                )
            ''', (session_id, session_id, self.max_history))
            
            deleted_count = cursor.rowcount
    
    def get_conversation_history(self, session_id: str = 'default', limit: int = None) -> List[Dict[str, Any]]:
        """Lấy lịch sử conversation cho session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        cursor.execute(f'''
            SELECT id, role, content, function_call, function_response, timestamp, created_at
            FROM conversation_history 
            WHERE session_id = ?
            ORDER BY timestamp ASC
            {limit_clause}
        ''', (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            message = {
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'function_call': json.loads(row[3]) if row[3] else None,
                'function_response': json.loads(row[4]) if row[4] else None,
                'timestamp': row[5],
                'created_at': row[6]
            }
            history.append(message)
        
        return history
    
    def get_recent_context(self, session_id: str = 'default', last_n_messages: int = 10) -> str:
        """
        Lấy context gần nhất để gửi cho AI model.
        Trả về formatted string phù hợp cho system prompt.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, role, content, function_call, function_response, timestamp, created_at
            FROM conversation_history 
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, last_n_messages))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return ""

        history = []
        for row in reversed(rows):
            message = {
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'function_call': json.loads(row[3]) if row[3] else None,
                'function_response': json.loads(row[4]) if row[4] else None,
                'timestamp': row[5],
                'created_at': row[6]
            }
            history.append(message)
        
        context_lines = []
        context_lines.append("💭 LỊCH SỬ CUỘC TRÒ CHUYỆN GẦN ĐÂY:")
        context_lines.append("")
        
        for i, msg in enumerate(history):
            role_label = "👤 Người dùng" if msg['role'] == 'user' else "🤖 Trợ lý"
            context_lines.append(f"{role_label}: {msg['content']}")

            if msg['function_call']:
                func_name = msg['function_call'].get('name', 'Unknown')
                func_args = msg['function_call'].get('args', {})
                context_lines.append(f"   ⚙️ Đã thực hiện: {func_name}")
                # Thêm thông tin quan trọng từ args
                if 'title' in func_args:
                    context_lines.append(f"   📝 Tiêu đề: {func_args['title']}")
                if 'start_time' in func_args:
                    context_lines.append(f"   🕐 Thời gian: {func_args['start_time']}")
            
            # Thêm khoảng cách giữa các tin nhắn
            if i < len(history) - 1:
                context_lines.append("")
        
        context_lines.append("")
        context_lines.append("🎯 HÃY SỬ DỤNG THÔNG TIN TRÊN để hiểu bối cảnh và trả lời phù hợp.")
        context_lines.append("---")
        return "\n".join(context_lines)
    
    def clear_session(self, session_id: str = 'default') -> int:
        """Xóa toàn bộ lịch sử của một session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM conversation_history WHERE session_id = ?
        ''', (session_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_session_stats(self, session_id: str = 'default') -> Dict[str, Any]:
        """Lấy thống kê của session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tổng số messages
        cursor.execute('''
            SELECT COUNT(*) FROM conversation_history WHERE session_id = ?
        ''', (session_id,))
        total_messages = cursor.fetchone()[0]
        
        # Message đầu tiên và cuối cùng
        cursor.execute('''
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM conversation_history WHERE session_id = ?
        ''', (session_id,))
        min_time, max_time = cursor.fetchone()
        
        # Đếm theo role
        cursor.execute('''
            SELECT role, COUNT(*) 
            FROM conversation_history 
            WHERE session_id = ? 
            GROUP BY role
        ''', (session_id,))
        role_counts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'session_id': session_id,
            'total_messages': total_messages,
            'first_message': min_time,
            'last_message': max_time,
            'user_messages': role_counts.get('user', 0),
            'assistant_messages': role_counts.get('assistant', 0)
        }
    
    def search_conversations(self, query: str, session_id: str = 'default', limit: int = 10) -> List[Dict[str, Any]]:
        """Tìm kiếm trong lịch sử conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, role, content, timestamp, created_at
            FROM conversation_history 
            WHERE session_id = ? AND content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, f'%{query}%', limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'timestamp': row[3],
                'created_at': row[4]
            })
        
        return results
