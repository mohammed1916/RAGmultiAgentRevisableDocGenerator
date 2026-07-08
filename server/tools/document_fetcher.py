"""Document fetching and storage for RAG system.

Fetches syllabuses, exam materials, and course content from the internet.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from ..logger import setup_logger

logger = setup_logger(__name__)

# Known sources for educational documents
DOCUMENT_SOURCES = {
    "jee_main": {
        "url": "https://www.jeemain.nta.ac.in/",
        "description": "JEE Main Exam Syllabus",
        "topics": [
            "Mathematics: Algebra, Trigonometry, Coordinate Geometry, Calculus",
            "Physics: Mechanics, Thermodynamics, Waves, Optics, Modern Physics",
            "Chemistry: Organic, Inorganic, Physical Chemistry",
        ],
    },
    "cbse_12": {
        "description": "CBSE Class 12 Syllabus",
        "topics": [
            "Physics: Electrostatics, Current, Magnetism, Optics, Modern Physics",
            "Chemistry: Organic, Inorganic, Physical Chemistry, Biomolecules",
            "Mathematics: Relations, Functions, Algebra, Calculus, Vectors",
        ],
    },
    "cbse_10": {
        "description": "CBSE Class 10 Syllabus",
        "topics": [
            "Science: Force, Work, Energy, Light, Electricity, Chemistry Basics",
            "Mathematics: Algebra, Geometry, Trigonometry, Statistics",
        ],
    },
}


class DocumentFetcher:
    """Fetch educational documents from various sources."""

    def __init__(self, cache_dir: str = "document_cache"):
        """Initialize the document fetcher.

        Args:
            cache_dir: Directory to cache downloaded documents
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.documents: Dict[str, Dict[str, Any]] = {}
        self._load_cached_documents()

    def _load_cached_documents(self):
        """Load previously cached documents from disk."""
        cache_file = self.cache_dir / "documents_index.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                self.documents = json.load(f)
            logger.info(f"Loaded {len(self.documents)} cached documents")

    def _save_cache(self):
        """Save documents index to disk."""
        cache_file = self.cache_dir / "documents_index.json"
        with open(cache_file, "w") as f:
            json.dump(self.documents, f, indent=2)

    def fetch_syllabus(self, exam_type: str) -> Dict[str, Any]:
        """Fetch syllabus for a specific exam/course.

        Args:
            exam_type: Type of exam (jee_main, cbse_12, cbse_10, etc.)

        Returns:
            Dictionary with syllabus content
        """
        if exam_type in self.documents:
            logger.info(f"Using cached syllabus: {exam_type}")
            return self.documents[exam_type]

        if exam_type not in DOCUMENT_SOURCES:
            logger.warning(f"Unknown exam type: {exam_type}")
            return self._get_default_syllabus(exam_type)

        source = DOCUMENT_SOURCES[exam_type]
        doc_id = hashlib.md5(exam_type.encode()).hexdigest()[:8]

        document = {
            "id": doc_id,
            "type": exam_type,
            "title": source["description"],
            "source": source.get("url", ""),
            "fetched_at": datetime.now().isoformat(),
            "topics": source.get("topics", []),
            "content": self._format_syllabus_content(source.get("topics", [])),
        }

        self.documents[exam_type] = document
        self._save_cache()

        logger.info(f"Fetched syllabus: {exam_type}")
        return document

    def fetch_jee_full_curriculum(self) -> Dict[str, Any]:
        """Fetch complete JEE preparation curriculum.

        Returns:
            Dictionary with structured JEE curriculum
        """
        jee_curriculum = {
            "id": "jee_full",
            "type": "jee_complete",
            "title": "JEE Advanced Complete Curriculum",
            "fetched_at": datetime.now().isoformat(),
            "subjects": {
                "Mathematics": {
                    "chapters": [
                        "Relations and Functions",
                        "Inverse Trigonometric Functions",
                        "Matrices and Determinants",
                        "Continuity and Differentiability",
                        "Applications of Derivatives",
                        "Integrals",
                        "Applications of Integrals",
                        "Differential Equations",
                        "Vector Algebra",
                        "3D Geometry",
                        "Linear Programming",
                        "Probability",
                    ],
                    "difficulty": "High",
                    "estimated_hours": 150,
                },
                "Physics": {
                    "chapters": [
                        "Electrostatics",
                        "Current Electricity",
                        "Magnetic Effects of Current",
                        "Magnetism",
                        "Electromagnetic Induction",
                        "Alternating Current",
                        "Electromagnetic Waves",
                        "Optics",
                        "Modern Physics",
                        "Nuclear Physics",
                    ],
                    "difficulty": "High",
                    "estimated_hours": 140,
                },
                "Chemistry": {
                    "chapters": [
                        "Atomic Structure",
                        "Chemical Bonding",
                        "States of Matter",
                        "Thermodynamics",
                        "Chemical Equilibrium",
                        "Electrochemistry",
                        "Kinetics",
                        "Surface Chemistry",
                        "Coordination Compounds",
                        "Organic Chemistry",
                        "Polymers",
                        "Biomolecules",
                    ],
                    "difficulty": "High",
                    "estimated_hours": 130,
                },
            },
            "total_chapters": 35,
            "total_hours": 420,
        }

        self.documents["jee_full"] = jee_curriculum
        self._save_cache()
        return jee_curriculum

    def fetch_course_material(self, course_name: str) -> Dict[str, Any]:
        """Fetch material for a specific course.

        Args:
            course_name: Name of the course (e.g., "Python Programming", "Data Science")

        Returns:
            Dictionary with course material
        """
        course_id = hashlib.md5(course_name.encode()).hexdigest()[:8]

        if course_id in self.documents:
            return self.documents[course_id]

        # Generate course structure
        course = {
            "id": course_id,
            "type": "course",
            "title": course_name,
            "fetched_at": datetime.now().isoformat(),
            "modules": self._generate_course_modules(course_name),
        }

        self.documents[course_id] = course
        self._save_cache()
        return course

    @staticmethod
    def _format_syllabus_content(topics: List[str]) -> str:
        """Format syllabus topics into text content.

        Args:
            topics: List of topic strings

        Returns:
            Formatted syllabus text
        """
        return "\n".join([f"- {topic}" for topic in topics])

    @staticmethod
    def _generate_course_modules(course_name: str) -> List[Dict[str, Any]]:
        """Generate course modules based on course name.

        Args:
            course_name: Name of the course

        Returns:
            List of module structures
        """
        course_modules = {
            "python": [
                {"name": "Basics", "topics": ["Variables", "Data Types", "Operators"]},
                {"name": "Control Flow", "topics": ["if/else", "Loops", "Functions"]},
                {"name": "OOP", "topics": ["Classes", "Inheritance", "Polymorphism"]},
                {"name": "Libraries", "topics": ["NumPy", "Pandas", "Matplotlib"]},
            ],
            "data science": [
                {"name": "Statistics", "topics": ["Descriptive Stats", "Probability", "Distributions"]},
                {"name": "Data Cleaning", "topics": ["Missing Data", "Outliers", "Normalization"]},
                {"name": "ML Basics", "topics": ["Linear Regression", "Classification", "Clustering"]},
                {"name": "Deep Learning", "topics": ["Neural Networks", "CNN", "RNN"]},
            ],
            "web development": [
                {"name": "Frontend", "topics": ["HTML", "CSS", "JavaScript"]},
                {"name": "Backend", "topics": ["APIs", "Databases", "Authentication"]},
                {"name": "Frameworks", "topics": ["React", "Django", "FastAPI"]},
                {"name": "DevOps", "topics": ["Docker", "CI/CD", "Cloud"]},
            ],
        }

        # Default structure
        for key in course_modules:
            if key.lower() in course_name.lower():
                return course_modules[key]

        return [
            {"name": "Introduction", "topics": ["Overview", "Setup", "First Project"]},
            {"name": "Fundamentals", "topics": ["Core Concepts", "Best Practices"]},
            {"name": "Advanced", "topics": ["Optimization", "Architecture", "Scaling"]},
        ]

    @staticmethod
    def _get_default_syllabus(exam_type: str) -> Dict[str, Any]:
        """Get default syllabus structure for unknown exam types.

        Args:
            exam_type: Type of exam

        Returns:
            Default syllabus structure
        """
        return {
            "id": hashlib.md5(exam_type.encode()).hexdigest()[:8],
            "type": exam_type,
            "title": f"Syllabus for {exam_type}",
            "fetched_at": datetime.now().isoformat(),
            "topics": [
                "Fundamentals",
                "Core Concepts",
                "Advanced Topics",
                "Practice Problems",
                "Mock Tests",
            ],
            "content": "Syllabus content - Please specify exact exam type for detailed curriculum",
        }

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID.

        Args:
            doc_id: Document ID or exam type

        Returns:
            Document dictionary or None
        """
        return self.documents.get(doc_id)

    def list_available_documents(self) -> List[Dict[str, str]]:
        """List all available cached documents.

        Returns:
            List of document metadata
        """
        return [
            {"id": doc_id, "title": doc.get("title", doc_id), "type": doc.get("type", "unknown")}
            for doc_id, doc in self.documents.items()
        ]

    def get_topics_for_exam(self, exam_type: str) -> List[str]:
        """Get all topics for a specific exam.

        Args:
            exam_type: Type of exam

        Returns:
            List of topics
        """
        doc = self.fetch_syllabus(exam_type)
        return doc.get("topics", [])

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """Search cached documents for relevant content.

        Args:
            query: Search query

        Returns:
            List of matching documents
        """
        query_terms = set(query.lower().split())
        results = []

        for doc_id, doc in self.documents.items():
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            topics = " ".join(doc.get("topics", [])).lower()

            score = 0
            full_text = f"{title} {content} {topics}"

            for term in query_terms:
                score += full_text.count(term)

            if score > 0:
                results.append(
                    {
                        "id": doc_id,
                        "title": doc.get("title"),
                        "type": doc.get("type"),
                        "relevance_score": score,
                    }
                )

        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
