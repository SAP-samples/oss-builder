from dataclasses import dataclass
import difflib
import lizard


@dataclass
class Diff:
    filename: str
    file_before: str
    file_after: str

    def get_unified_diff(self) -> str:
        return ''.join(difflib.unified_diff(
                self.file_before.splitlines(keepends=True),
                self.file_after.splitlines(keepends=True),
                fromfile=self.filename + ' (vulnerable)',
                tofile=self.filename + ' (fix commit)',
            ))

    def _get_changed_lines(self) -> set[int]:
        differ = difflib.Differ()
        diff = differ.compare(self.file_before.splitlines(keepends=True),
                              self.file_after.splitlines(keepends=True))
        changed_lines = set()
        num = 0
        for line in diff:
            if line.startswith('-'):
                changed_lines.add(num)
            elif line.startswith('+'):
                changed_lines.add(num)
                num += 1
            else:
                num += 1
        return set(changed_lines)

    # TODO(liam) introduce a before and after variant
    def get_changed_functions(self, before=True) -> set[lizard.FunctionInfo]:
        analyzer = lizard.analyze_file.analyze_source_code(
                self.filename,
                self.file_before if before else self.file_after
            )
        changed_lines = self._get_changed_lines()
        changed_functions = set()
        for function in analyzer.function_list:
            for line in range(function.start_line, function.end_line):
                if line in changed_lines:
                    changed_functions.add(function)

        return changed_functions
