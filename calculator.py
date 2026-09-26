"""受限数学语法：只解析数字、四则运算、括号和一元正负号。"""

from decimal import Decimal, DecimalException, localcontext
import re

MAX_LENGTH = 200
MAX_DEPTH = 40
MAX_VALUE = Decimal("1e100")
TOKEN_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]*)?|\.[0-9]+|[+\-*/()]")


class CalculationError(ValueError):
    """可以安全地向用户展示的计算错误。"""


class Parser:
    """递归下降：expression → term → factor，体现运算优先级。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def peek(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def take(self):
        token = self.peek()
        self.position += 1
        return token

    @staticmethod
    def checked(value):
        if not value.is_finite() or abs(value) > MAX_VALUE:
            raise CalculationError("计算结果超出范围，请使用较小的数字。")
        return value

    def expression(self, depth=0):
        value = self.term(depth)
        while self.peek() in ("+", "-"):
            operator = self.take()
            right = self.term(depth)
            value = self.checked(value + right if operator == "+" else value - right)
        return value

    def term(self, depth):
        value = self.factor(depth)
        while self.peek() in ("*", "/"):
            operator = self.take()
            right = self.factor(depth)
            if operator == "/" and right == 0:
                raise CalculationError("除数不能为 0。")
            value = self.checked(value * right if operator == "*" else value / right)
        return value

    def factor(self, depth):
        if depth >= MAX_DEPTH:
            raise CalculationError("括号或正负号嵌套过多，请简化表达式。")
        token = self.take()
        if token in ("+", "-"):
            value = self.factor(depth + 1)
            return value if token == "+" else -value
        if token == "(":
            value = self.expression(depth + 1)
            if self.take() != ")":
                raise CalculationError("括号不匹配，请检查左括号和右括号。")
            return value
        if token is None or token in ("*", "/", ")"):
            raise CalculationError("表达式不完整或运算符位置不正确。")
        return self.checked(Decimal(token))


def calculate_expression(expression):
    """返回规范化表达式和十进制结果字符串；不执行用户提供的代码。"""
    if not isinstance(expression, str):
        raise CalculationError("expression 必须是字符串。")
    expression = expression.strip()
    if not expression:
        raise CalculationError("请输入表达式。")
    if len(expression) > MAX_LENGTH:
        raise CalculationError("表达式最多支持 200 个字符。")
    expression = expression.replace("×", "*").replace("÷", "/").replace("−", "-")

    tokens = []
    position = 0
    while position < len(expression):
        if expression[position].isspace():
            position += 1
            continue
        match = TOKEN_PATTERN.match(expression, position)
        if not match:
            raise CalculationError("只支持数字、小数点、+ - × ÷ 和英文括号。")
        tokens.append(match.group())
        position = match.end()

    try:
        with localcontext() as context:
            context.prec = 28
            parser = Parser(tokens)
            value = parser.expression()
            if parser.peek() is not None:
                raise CalculationError("表达式格式不正确，请检查运算符和括号。")
            # 不通过浮点数转换；例如 0.1 + 0.2 可以准确输出 0.3。
            result = format(value, "f")
            if "." in result:
                result = result.rstrip("0").rstrip(".")
            if value == 0:
                result = "0"
    except DecimalException as error:
        raise CalculationError("数字无法计算，请检查数值范围。") from error
    return expression, result
