import codeql
from lizard import FunctionInfo
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union
from transformers import AutoTokenizer


@dataclass
class Location:
    line: int
    column: int


@dataclass(frozen=True)
class FileLocation:
    start_line: int
    filename: str

    def toDict(self) -> dict[str, Union[int, str]]:
        return {'start_line': self.start_line, 'filename': self.filename}


class Rewriter(ABC):
    src: list[str]
    database: codeql.Database
    function_info: FunctionInfo
    comment_prefix = '//?!!'
    # TODO(liam) this should be part of the value returned by rewrite
    included: set[FileLocation] = set()

    def __init__(self, src: list[str], function_info: FunctionInfo,
                 database: codeql.Database):
        self.src = src
        self.function_info = function_info
        self.database = database

    def append_comment_at_line(self, line_num: int, comment: str) -> None:
        """
        Args:
            line_num: The line to insert the comment above (one indexed)
            comment: The comment to insert
        """

        self.src[line_num] = self.src[line_num] + f' {self.comment_prefix} '\
            + comment

    def append_comment_at_location(self, location: Location,
                                   comment: str) -> None:
        comment = f' /* {comment} */'
        self.src[location.line] = self.src[location.line][:location.column] \
            + comment \
            + self.src[location.line][location.column:]

    @abstractmethod
    def rewrite(self) -> list[str]:
        pass


class EnumConstantResolver(Rewriter):
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = f"""
import cpp

from File file, Function func, EnumConstant const, EnumConstantAccess acc
where func.getFile() = file
and const.getAnAccess() = acc
and acc.getEnclosingFunction() = func
and not exists(EnumConstantAccess prev_acc |
    prev_acc.getEnclosingFunction() = func and
    prev_acc.getLocation().getStartLine() < acc.getLocation().getStartLine()
    and prev_acc.getTarget() = acc.getTarget()
)
select file.getRelativePath(),
       file.getAbsolutePath(),
       func.getLocation().getStartLine(),
       acc.getLocation().getStartLine(),
       const.getDeclaringEnum(),
       const.getValue(),
       const
"""
        result = self.database.query(query)[1:]
        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )
        for enum_usage in result:
            line = int(enum_usage[0])
            enum_type = enum_usage[1]
            enum_value = enum_usage[2]
            enum_const_name = enum_usage[3]
            comment = f'enum const {enum_const_name} = {enum_value}'
            if enum_type != '(unnamed enum)':
                comment += f' of {enum_type}'
            line = line - fi.start_line
            self.append_comment_at_line(line, comment)

        return self.src
    

class ShortMacroResolver(Rewriter):
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = f"""
import cpp

from
    File file,
    Function func,
    Macro macro,
    MacroAccess acc
 where 
    func.getFile() = file
    and acc.getFile() = file
    and acc.getLocation().getStartLine() > func.getLocation().getStartLine()
    and acc.getLocation().getEndLine() < func.getBlock().getLastStmt().getLocation().getEndLine()
    and acc.getMacro() = macro
    and macro.getBody().length() < 20
    and not exists(MacroAccess prev_acc |
        prev_acc.getLocation().getStartLine() > func.getLocation().getStartLine()
        and prev_acc.getLocation().getStartLine() < acc.getLocation().getStartLine()
        and prev_acc.getMacro() = acc.getMacro()
    )
select 
    file.getRelativePath(),
    file.getAbsolutePath(),
    func.getLocation().getStartLine(),
    acc.getLocation().getStartLine(),
    macro.getName(),
    macro.getBody(),
    macro.getFile().getRelativePath()
"""
        result = self.database.query(query)[1:]
        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )
        for macro_access in result:
            line = int(macro_access[0])
            macro_name = macro_access[1]
            macro_body = macro_access[2]
            comment = f'macro {macro_name} = {macro_body}'
            line = line - fi.start_line
            self.append_comment_at_line(line, comment)

        return self.src


class IntegralTypedefResolver(Rewriter):
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = f"""
import cpp

from
    File file,
    Function func,
    Type type,
    string typename,
    string resolved_typename,
    Element element
 where 
    func.getFile() = file
    and element = type.getATypeNameUse()
    and element.getFile() = file
    and element.getLocation().getStartLine() > func.getLocation().getStartLine()
    and element.getLocation().getEndLine() < func.getBlock().getLastStmt().getLocation().getEndLine()
    and type.getName() = typename
    and type.resolveTypedefs().(IntegralType).getName() = resolved_typename
    and typename != resolved_typename
    and not resolved_typename.matches("%unnamed%")
    and not resolved_typename.matches("%.%")
    and not exists(Element prev_element, Type other_type |
        prev_element.getLocation().getStartLine() > func.getLocation().getStartLine()
        and prev_element.getLocation().getStartLine() < element.getLocation().getStartLine()
        and prev_element = other_type.getATypeNameUse()
        and other_type.getName() = typename
        and other_type.resolveTypedefs().getName() = resolved_typename
    )
select
    file.getRelativePath(),
    file.getAbsolutePath(),
    func.getLocation().getStartLine(),
    element.getLocation().getStartLine(),
    typename,
    resolved_typename
"""
        result = self.database.query(query)[1:]
        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )
        for type_access in result:
            line = int(type_access[0])
            typename = type_access[1]
            resolved_type = type_access[2]
            comment = f'typedef {typename} {resolved_type}'
            line = line - fi.start_line
            self.append_comment_at_line(line, comment)

        return self.src


class GlobalVariableResolver(Rewriter):
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = f"""
import cpp

from File file,
     Function func,
     GlobalVariable var,
     VariableAccess acc,
     Expr assigned,
     string value
where
func.getFile() = file
and var.getAnAccess() = acc
and acc.getEnclosingFunction() = func
and var.getAnAssignedValue() = assigned
and if exists(assigned.getValue())
    then value = assigned.getValue()
    else value = assigned.toString()
and not exists(VariableAccess prev_acc |
    prev_acc.getEnclosingFunction() = func and
    prev_acc.getLocation().getStartLine() < acc.getLocation().getStartLine()
    and prev_acc.getTarget() = acc.getTarget()
)
select file.getRelativePath(),
       file.getAbsolutePath(),
       func.getLocation().getStartLine(),
       var,
       var.getUnderlyingType(),
       value,
       acc.getLocation().getStartLine()"""
        result = self.database.query(query)[1:]

        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )

        # group by variable name
        var_map: dict[str, list[list[str]]] = {}
        for res in result:
            var_name = res[0]
            if var_name not in var_map:
                var_map[var_name] = []
            var_map[var_name].append(res)

        for var_name, usages in var_map.items():
            comment = f'global variable {var_name} ({usages[0][1]})'
            values = list(set(u[2] for u in usages))
            # split values into values containingn '...' and those that don't
            unabr = [v for v in values if '...' not in v]
            if len(unabr) == 1 and len(values) > 1:
                comment += ', value e.g. ' + unabr[0]
            elif len(unabr) > 0:
                comment += ' is: ' + ' or '.join(sorted(unabr[:4]))
                if len(unabr) < len(values) or len(unabr) > 4:
                    comment += ', ...'
            line = int(usages[0][3]) - fi.start_line
            self.append_comment_at_line(line, comment)
        return self.src


class NegativeTaintResolver(Rewriter):
    """
    Infer function arguments that are most likely not ACID, because we can
    determine their value statically
    """
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = f"""
import cpp

from File file,
     Function func,
     Parameter param,
     int paramIdx,
     Expr arg,
     Call call,
     string value
where
func.getFile() = file and
func.getAParameter() = param and
param.getIndex() = paramIdx and
func.getACallToThisFunction() = call and
call.getArgument(paramIdx) = arg and
(
    if exists(arg.getValue())
     then value = arg.getValue().toString()
    else value = "<null>"
)
select 
    file.getRelativePath(),
    file.getAbsolutePath(),
    func.getLocation().getStartLine(),
    paramIdx,
    value,
    param.getLocation().getEndLine(),
    param.getLocation().getEndColumn()"""
        result = self.database.query(query)[1:]

        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )

        # group by parameter index
        param_map: dict[int, list[list[str]]] = {}
        for res in result:
            param_idx = int(res[0])
            if param_idx not in param_map:
                param_map[param_idx] = []
            param_map[param_idx].append(res)

        for param_idx in param_map:
            # discard where there is an unknown input
            if '<null>' in [r[1] for r in param_map[param_idx]]:
                continue
            # append a comment where the values are known
            line = int(param_map[param_idx][0][2]) - fi.start_line
            col = int(param_map[param_idx][0][3])
            values = [r[1] for r in param_map[param_idx]]
            if len(values) <= 3:
                comment = f'non attacker controlled value: {", ".join(values)}'
            else:
                comment = 'non attacker controlled value'
            self.append_comment_at_location(Location(line, col), comment)
        return self.src


class RemoteSourceFlow(Rewriter):
    """
    Infer function arguments that are most likely not ACID, because we can
    determine their value statically
    """
    def rewrite(self) -> list[str]:
        fi = self.function_info
        query = """
import cpp
import semmle.code.cpp.dataflow.new.DataFlow
import semmle.code.cpp.security.FlowSources as FlowSources

module TaintedParamtersConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
      source instanceof FlowSources::RemoteFlowSource
  }
  predicate isSink(DataFlow::Node sink) {
    sink = sink // always true
  }
}
module TaintedParamtersFlow = DataFlow::Global<TaintedParamtersConfig>;

from
  File file,
  Function func,
  DataFlow::Node source,
  DataFlow::Node sink
where
  func.getFile() = file
  and func.getAParameter() = sink.asParameter()
  and TaintedParamtersFlow::flow(source, sink)
select
  file.getRelativePath(),
  file.getAbsolutePath(),
  func.getLocation().getStartLine(),
  source.toString(),
  sink.asParameter().getLocation().getEndLine(),
  sink.asParameter().getLocation().getEndColumn()"""
        result = self.database.query(query)[1:]

        # filter so that only results of this function are processed
        # query is generic for all functions to make it cacheable
        result = list(
            map(
                lambda x: x[3:], # discard filename and start line
                filter(
                    lambda t: (t[0] == fi.filename or t[1] == fi.filename) \
                        and int(t[2]) == fi.start_line,
                    result
                )
            )
        )

        for parameter in result:
            line = int(parameter[1]) - fi.start_line
            col = int(parameter[2])
            comment = f'data flow from {parameter[0]}'
            self.append_comment_at_location(Location(line, col), comment)
        return self.src


def get_function(path: str, start: int, end: int) -> str:
    with open(path, 'r') as f:
        lines = f.readlines()
    return ''.join(lines[start-1:end+1])


class CalleeContext(Rewriter):
    """
    Copy the source code of a called functions and calling functions
    in the context, based on a "inlining"/copying heuristic
    """

    """
    Maximal length `self.src` is expanded to. Regarding the concrete value, it
    is chosen arbitrarily, based on taking a somehow long function and adding
    a bit to it. In the future we may want to choose a more systematic way
    of setting it, or set it based on a concrete model we use.
    """
    max_len: int = 16384
    tokenizer = AutoTokenizer.from_pretrained("codellama/CodeLlama-7b-hf")

    def size(self, fun: str) -> int:
        return len(self.tokenizer(fun)['input_ids'])
    
    def _inner_rewrite(self, src, function_info):
        # split into lines for the rewriters
        # join back together at the end
        src = src.split("\n")
        rewriters = [
            EnumConstantResolver,
            ShortMacroResolver,
            IntegralTypedefResolver,
            GlobalVariableResolver,
            NegativeTaintResolver,
            RemoteSourceFlow,
        ]
        for rewriter in rewriters:
            src = rewriter(src, function_info, self.database)\
                        .rewrite()
        return "\n".join(src)

    def get_next(self) -> bool:
        query = """
import cpp

from
    Function included,
    Function candidate
where
    (included.calls(candidate) /*or candidate.calls(included)*/)
    and candidate.getFile().getAbsolutePath().length() != 0
select
    included.getFile().getRelativePath(),
    included.getFile().getAbsolutePath(),
    included.getLocation().getStartLine(),
    candidate.getFile().getRelativePath(),
    candidate.getFile().getAbsolutePath(),
    candidate.getLocation().getStartLine(),
    candidate.getBlock().getLastStmt().getLocation().getEndLine()"""
        result = self.database.query(query)[1:]

        # query is cacheable
        # filter all candidates such that included is really included
        # and candidate is not yet included
        def should_be_included(res):
            return any(
                (res[0] == location.filename or res[1] == location.filename) and int(res[2]) == location.start_line
                for location in self.included
            ) and all(
                not ((res[3] == location.filename or res[4] == location.filename) and int(res[5]) == location.start_line)
                for location in self.included
            )
        candidates = filter(
            should_be_included,
            result
        )
        
        # add location and function source code
        def get_fun(res: list[str]) -> str:
            return self._inner_rewrite(
                get_function(res[4], int(res[5]), int(res[6])),
                FunctionInfo("PLACEHOLDER", res[4], int(res[5]))
            )
        candidates = [
            (
                FileLocation(start_line=int(res[5]), filename=res[4]),
                get_fun(res),
            )
            for res in candidates
        ]

        # sort from largest to smallest
        candidates.sort(key=lambda x: self.size(x[1]), reverse=True)
        initial_budget = self.max_len // 4
        round_budget = initial_budget
        for loc, fun in candidates:
            if self.size('\n'.join(self.src)) + self.size(fun) < self.max_len \
               and round_budget > 0:
                round_budget -= self.size(fun)
                self.src += fun.split('\n')
                self.included.add(loc)
            else:
                return self.size('\n'.join(self.src)) < self.max_len \
                        and round_budget < initial_budget
        return round_budget < initial_budget

    def rewrite(self) -> list[str]:
        fi = self.function_info
        self.included.add(FileLocation(start_line=fi.start_line,
                                       filename=fi.filename))
        # TODO(liam) this code does not look so nice
        while self.get_next():
            pass
        return self.src


class RewritePipeline(Rewriter):
    def rewrite(self) -> list[str]:
        rewriters = [EnumConstantResolver,
                     ShortMacroResolver,
                     IntegralTypedefResolver,
                     GlobalVariableResolver,
                     NegativeTaintResolver,
                     RemoteSourceFlow,
                     CalleeContext,
                     ]
        for rewriter in rewriters:
            self.src = rewriter(self.src, self.function_info, self.database)\
                        .rewrite()
        return self.src
