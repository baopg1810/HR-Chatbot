import ast
import operator

from langchain_core.tools import tool

from app.models.schemas import EscalationCreate, TicketPriority
from app.services.hris import get_personal_hr_metrics
from app.services.retrieval import search_policy_chunks
from app.services.tickets import create_ticket

# Safe operator mapping for calculator
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


@tool
def search_knowledge(query: str) -> str:
    """Tìm kiếm thông tin trong knowledge base.

    Args:
        query: Câu hỏi cần tìm kiếm

    Returns:
        Kết quả tìm kiếm
    """
    # TODO: Implement actual search logic (e.g., RAG with vector store)
    return f"Kết quả tìm kiếm cho: {query}"


def search_policy_tool(query: str, user, limit: int = 5):
    """Search readable HR policy chunks for the current user."""
    return search_policy_chunks(query, user, limit=limit)


def get_hr_metrics_tool(user):
    """Return personal HR metrics for the current user."""
    return get_personal_hr_metrics(user)


async def create_ticket_tool(
    user,
    session_id: str | None,
    message: str,
    reason: str = "user_requested",
    priority: TicketPriority = "normal",
    db=None,
):
    """Create an HR escalation ticket using the existing ticket service."""
    return await create_ticket(
        user,
        EscalationCreate(
            session_id=session_id,
            message=message,
            reason=reason if reason in {"no_source", "outside_scope", "sensitive", "user_requested", "low_confidence"} else "user_requested",
            priority=priority,
        ),
        db=db,
    )


@tool
def calculate(expression: str) -> str:
    """Tính toán biểu thức toán học an toàn (không dùng eval).

    Hỗ trợ: +, -, *, /, //, %, ** và dấu ngoặc.

    Args:
        expression: Biểu thức cần tính (ví dụ: "2 + 3 * 4")

    Returns:
        Kết quả tính toán
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return str(result)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
        return f"Lỗi tính toán: {e}"


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate AST node using safe operators only."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.UnaryOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_eval_node(node.operand))
    elif isinstance(node, ast.BinOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_eval_node(node.left), _eval_node(node.right))
    else:
        raise ValueError(f"Unsupported expression: {type(node).__name__}")
