"""Mock data for testing document generation without Ollama."""

from .models import ExecutionPlan, Task, DocumentSection


class MockData:
    """Provides realistic mock data for testing."""

    @staticmethod
    def get_jee_study_plan():
        """Mock JEE study plan."""
        return ExecutionPlan(
            document_type="JEE Mathematics Study Plan",
            assumptions={
                "exam_date": "12 months from now",
                "daily_study_hours": "6 hours",
                "current_level": "Intermediate",
                "target_score": "280/300",
            },
            tasks=[
                Task(id=1, description="Study Relations and Functions", dependencies=[]),
                Task(id=2, description="Practice 50 problems", dependencies=[1]),
                Task(id=3, description="Study Matrices", dependencies=[]),
                Task(id=4, description="Complete Mock Test 1", dependencies=[1, 3]),
                Task(id=5, description="Revise Weak Areas", dependencies=[4]),
            ],
            outline=[
                "Executive Summary",
                "Topics to Cover",
                "Study Schedule",
                "Practice Problems",
                "Mock Tests",
                "Revision Strategy",
            ],
        )

    @staticmethod
    def get_cbse_study_plan():
        """Mock CBSE Class 12 study plan."""
        return ExecutionPlan(
            document_type="CBSE Class 12 Physics Study Plan",
            assumptions={
                "exam_date": "3 months",
                "daily_study_hours": "4 hours",
                "chapters": "Electrostatics, Current, Magnetism, Optics",
            },
            tasks=[
                Task(id=1, description="Study Electrostatics Chapter", dependencies=[]),
                Task(id=2, description="Solve NCERT Problems", dependencies=[1]),
                Task(id=3, description="Solve Previous Year Papers", dependencies=[1, 2]),
                Task(id=4, description="Revise and Self-Assessment", dependencies=[3]),
            ],
            outline=[
                "Chapter Overview",
                "Key Concepts",
                "Solved Examples",
                "Practice Problems",
                "Assessment",
            ],
        )

    @staticmethod
    def get_python_course_plan():
        """Mock Python programming course plan."""
        return ExecutionPlan(
            document_type="Python Programming Course - Week 1",
            assumptions={
                "level": "Beginner",
                "duration": "8 weeks",
                "coding_hours": "3 hours/day",
            },
            tasks=[
                Task(id=1, description="Setup Python environment", dependencies=[]),
                Task(id=2, description="Learn Variables and Data Types", dependencies=[1]),
                Task(id=3, description="Write first program", dependencies=[2]),
                Task(id=4, description="Complete coding exercises", dependencies=[3]),
            ],
            outline=[
                "Learning Objectives",
                "Setup Instructions",
                "Core Concepts",
                "Hands-on Exercises",
                "Mini Project",
            ],
        )

    @staticmethod
    def get_mock_sections_jee():
        """Mock generated sections for JEE plan."""
        return [
            DocumentSection(
                title="Executive Summary",
                content="""This comprehensive 12-month study plan is designed to prepare students for the JEE Mathematics
                examination. The plan covers all major topics including Relations and Functions, Matrices, Calculus, and Vectors.
                With consistent effort of 6 hours daily, students can achieve a target score of 280/300.""",
                heading_level=1,
            ),
            DocumentSection(
                title="Topics to Cover",
                content="""The JEE Mathematics syllabus includes:
                1. Relations and Functions - Domain, Range, Inverse Functions
                2. Matrices and Determinants - Properties and Applications
                3. Calculus - Limits, Derivatives, Integrals, Applications
                4. Vectors - Scalar Triple Product, Vector Product
                5. Coordinate Geometry - Conic Sections, 3D Geometry""",
                heading_level=1,
            ),
            DocumentSection(
                title="Study Schedule",
                content="""Month 1-2: Fundamentals and Problem-Solving (Relations, Functions, Matrices)
                Month 3-6: Advanced Topics (Calculus, Vectors, Coordinate Geometry)
                Month 7-9: Practice and Mock Tests (Solving previous year papers)
                Month 10-12: Revision and Final Assessment (Focus on weak areas)""",
                heading_level=1,
            ),
            DocumentSection(
                title="Practice Problems",
                content="""Daily practice schedule:
                - 10 problems from current topic
                - 5 problems from previous topics
                - 2 problems from different chapters
                This ensures both depth and breadth in problem-solving skills.""",
                heading_level=1,
            ),
            DocumentSection(
                title="Mock Tests",
                content="""Complete full-length mock tests every 2 weeks:
                - Test duration: 3 hours
                - Total questions: 30
                - Marks: 120 (4 marks each)
                - Review and analysis after each test""",
                heading_level=1,
            ),
            DocumentSection(
                title="Revision Strategy",
                content="""In the final 2 months, focus on:
                - Revising weak topics identified in mock tests
                - Speed and accuracy improvement
                - Short-cut methods for complex problems
                - Time management practice""",
                heading_level=1,
            ),
        ]

    @staticmethod
    def get_mock_sections_cbse():
        """Mock generated sections for CBSE plan."""
        return [
            DocumentSection(
                title="Chapter Overview",
                content="""Electrostatics is a fundamental chapter in CBSE Class 12 Physics that deals with
                electric charges, fields, and potentials. This chapter is crucial for understanding electromagnetic phenomena
                and typically carries 8-10 marks in the board examination.""",
                heading_level=1,
            ),
            DocumentSection(
                title="Key Concepts",
                content="""Main topics to understand:
                1. Electric Charge and Coulomb's Law
                2. Electric Field and Field Lines
                3. Electric Potential and Potential Difference
                4. Equipotential Surfaces
                5. Capacitors and Dielectrics""",
                heading_level=1,
            ),
            DocumentSection(
                title="Solved Examples",
                content="""Example 1: Calculate the electric field due to two point charges
                Example 2: Find potential difference between two points
                Example 3: Determine capacitance of parallel plate capacitor
                Each example includes step-by-step solution and explanation of concepts used.""",
                heading_level=1,
            ),
            DocumentSection(
                title="Practice Problems",
                content="""NCERT Exercise Problems: 30 problems covering all concepts
                Previous Year Board Papers: 15 problems from past 5 years
                Challenging Problems: 10 higher-order thinking problems
                Estimated time: 20 hours of practice""",
                heading_level=1,
            ),
            DocumentSection(
                title="Assessment",
                content="""Self-assessment test (60 minutes, 20 marks):
                Covers all 5 main concepts
                Mix of short-answer and numerical problems
                Use this to identify weak areas and revise accordingly""",
                heading_level=1,
            ),
        ]

    @staticmethod
    def get_mock_sections_python():
        """Mock generated sections for Python course."""
        return [
            DocumentSection(
                title="Learning Objectives",
                content="""By the end of Week 1, you will be able to:
                1. Set up Python development environment
                2. Understand variables and data types
                3. Write basic Python programs
                4. Use print statements and input functions
                5. Perform basic mathematical operations""",
                heading_level=1,
            ),
            DocumentSection(
                title="Setup Instructions",
                content="""Step 1: Download Python 3.10+ from python.org
                Step 2: Install with PATH option enabled
                Step 3: Verify installation: python --version
                Step 4: Set up VS Code or PyCharm IDE
                Step 5: Create your first project folder""",
                heading_level=1,
            ),
            DocumentSection(
                title="Core Concepts",
                content="""Variables: Containers for storing data values
                Data Types: int, float, str, bool, list, dict, tuple
                Operators: Arithmetic, Comparison, Logical
                Input/Output: input() and print() functions
                Comments: Using # for single-line comments""",
                heading_level=1,
            ),
            DocumentSection(
                title="Hands-on Exercises",
                content="""Exercise 1: Create variables and perform calculations
                Exercise 2: Take user input and display output
                Exercise 3: Create a simple temperature converter
                Exercise 4: Build a basic calculator
                Estimated time: 3-4 hours per exercise""",
                heading_level=1,
            ),
            DocumentSection(
                title="Mini Project",
                content="""Build a simple Personal Information Manager:
                - Store name, age, email
                - Calculate next birthday
                - Store multiple entries in a list
                - Display information in formatted output
                This projects reinforces all Week 1 concepts.""",
                heading_level=1,
            ),
        ]
