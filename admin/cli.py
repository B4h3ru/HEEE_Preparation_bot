import argparse

from models.departments import create_department, list_departments
from models.subjects import create_subject, list_subjects_by_department
from models.questions import create_question
from models.options import add_option


def cmd_list_departments() -> None:
    for dept in list_departments():
        print(f"{dept['id']}: {dept['name']}")


def cmd_add_department(args: argparse.Namespace) -> None:
    dept_id = create_department(args.name)
    print(f"Created department #{dept_id}: {args.name}")


def cmd_list_subjects(args: argparse.Namespace) -> None:
    subjects = list_subjects_by_department(args.department_id)
    if not subjects:
        print("No subjects for this department.")
        return
    for subj in subjects:
        print(f"{subj['id']}: {subj['name']}")


def cmd_add_subject(args: argparse.Namespace) -> None:
    subj_id = create_subject(args.department_id, args.name)
    print(f"Created subject #{subj_id} in department #{args.department_id}: {args.name}")


def cmd_add_question(args: argparse.Namespace) -> None:
    explanation = args.explanation or None
    question_id = create_question(
        department_id=args.department_id,
        subject_id=args.subject_id,
        question_text=args.text,
        explanation=explanation,
    )
    print(f"Created question #{question_id}")

    for idx, opt_text in enumerate(args.options):
        is_correct = idx == args.correct_index
        opt_id = add_option(question_id, opt_text, is_correct=is_correct)
        print(f"  Option #{opt_id} ({'correct' if is_correct else 'wrong'}): {opt_text}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HEEE Bot Admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list-departments", help="List all departments")
    p_list.set_defaults(func=lambda a: cmd_list_departments())

    p_add_dept = subparsers.add_parser("add-department", help="Create a new department")
    p_add_dept.add_argument("name", help="Department name")
    p_add_dept.set_defaults(func=cmd_add_department)

    p_list_subj = subparsers.add_parser(
        "list-subjects", help="List all subjects in a department"
    )
    p_list_subj.add_argument("department_id", type=int, help="Department ID")
    p_list_subj.set_defaults(func=cmd_list_subjects)

    p_add_subj = subparsers.add_parser("add-subject", help="Create a new subject")
    p_add_subj.add_argument("department_id", type=int, help="Department ID")
    p_add_subj.add_argument("name", help="Subject name")
    p_add_subj.set_defaults(func=cmd_add_subject)

    p_add_q = subparsers.add_parser("add-question", help="Create a question with options")
    p_add_q.add_argument("department_id", type=int, help="Department ID")
    p_add_q.add_argument("subject_id", type=int, help="Subject ID")
    p_add_q.add_argument("text", help="Question text")
    p_add_q.add_argument(
        "--explanation",
        help="Optional explanation text",
    )
    p_add_q.add_argument(
        "--options",
        nargs="+",
        required=True,
        help="Answer options (at least 2)",
    )
    p_add_q.add_argument(
        "--correct-index",
        type=int,
        default=0,
        help="Index of correct option in --options (0-based)",
    )
    p_add_q.set_defaults(func=cmd_add_question)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

