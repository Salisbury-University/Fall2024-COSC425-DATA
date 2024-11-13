from __future__ import annotations

from typing import TYPE_CHECKING, List, Dict, Callable, Tuple

from academic_metrics.enums import AttributeTypes
from academic_metrics.AI import AbstractClassifier

if TYPE_CHECKING:
    from academic_metrics.utils import Utilities
    from academic_metrics.utils.taxonomy_util import Taxonomy

"""
If you want to get a dictionary back from AbstractClassifier.get_classification_results_by_doi() method
you can use this type.

The key, value pairs in the dictionary are:
    1. "top_categories": List[str] of top categories
    2. "mid_categories": List[str] of mid categories
    3. "low_categories": List[str] of low categories
    4. "themes": List[str] of themes
"""
ClassificationResultsDict = Dict[str, List[str]]

"""
If you want to get a tuple back from AbstractClassifier.get_classification_results_by_doi() method
you can use this type.

The order of the elements in the tuple is:
    1. List[str] of top categories
    2. List[str] of mid categories
    3. List[str] of low categories
    4. List[str] of themes
"""
ClassificationResultsTuple = Tuple[List[str], List[str], List[str], List[str]]


class ClassificationOrchestrator:
    """Manages the classification process for research abstracts.

    This class orchestrates the process of extracting DOIs and abstracts from a list of dictionaries containing crossref data,
    classifying them using the AbstractClassifier class, and injecting the results back into the original data.
    It also tracks unclassified items for monitoring and debugging purposes.

    Attributes:
        abstract_classifier_factory: Factory function that creates AbstractClassifier instances.
        taxonomy: Taxonomy instance containing the classification hierarchy. Not used directly, but required by the AbstractClassifier. and thus is passed in to the factory function.
        utilities: Utilities instance for attribute extraction.
        ai_api_key: API key for AI service access.
        unclassified_item_count: Number of items that couldn't be classified.
        unclassified_dois: List of DOIs that couldn't be classified.
        unclassified_abstracts: List of abstracts that couldn't be classified.
        unclassified_doi_abstract_dict: Dictionary mapping unclassified DOIs to abstracts.
        unclassified_items: List of complete metadata items that couldn't be classified.
        unclassified_details: Dictionary containing organized unclassified data:
            - dois: List of unclassified DOIs
            - abstracts: List of unclassified abstracts
            - items: List of unclassified metadata items

    Methods:
        Public:
            run_classification() -> List[Dict]:
                Processes and classifies a list of research metadata dictionaries.

            get_unclassified_item_count() -> int:
                Returns the number of unclassified items.

            get_unclassified_dois() -> List[str]:
                Returns the DOIs of unclassified items.

            get_unclassified_abstracts() -> List[str]:
                Returns the abstracts of unclassified items.

            get_unclassified_doi_abstract_dict() -> Dict[str, str]:
                Returns the DOI to abstract mapping dictionary for unclassified items.

            get_unclassified_items() -> List[Dict]:
                Returns the unclassified items.

            get_unclassified_details_dict() -> Dict:
                Returns the details of unclassified items.

        Private:
            _classification_orchestrator() -> List[Dict]:
                Core classification logic for processing research metadata.

            _inject_categories() -> None:
                Adds classification results to a research metadata dictionary.

            _extract_categories() -> ClassificationResultsDict | ClassificationResultsTuple:
                Gets classification results for a specific DOI.

            _make_doi_abstract_dict() -> Dict[str, str]:
                Creates a DOI to abstract mapping dictionary.

            _retrieve_doi_abstract() -> Tuple[str, str]:
                Extracts DOI and abstract from a research metadata dictionary.

            _update_classified_instance_variables() -> None:
                Updates tracking variables for unclassified items.

            _set_classification_ran_true() -> None:
                Sets the classification ran flag to true.

            _has_ran_classification() -> bool:
                Checks if classification has been run.

            _validate_classification_ran() -> None:
                Validates if classification has been run.

    Example:
        >>> # Create wrapper instance
        >>> wrapper = ClassificationWrapper(
        ...     abstract_classifier_factory=create_classifier,
        ...     taxonomy=taxonomy,
        ...     utilities=utilities,
        ...     ai_api_key="your-api-key"
        ... )
        >>>
        >>> # Process research metadata
        >>> data = [
        ...     {"DOI": "10.1234/example", "abstract": "Research text..."},
        ...     {"DOI": "10.5678/sample", "abstract": "More research..."}
        ... ]
        >>> classified_data = wrapper.run_classification(data)
        >>>
        >>> # Access classification results
        >>> print(classified_data[0]["categories"])
        >>>
        >>> # Check unclassified items
        >>> print(f"Failed to classify {wrapper.unclassified_item_count} items")
    """

    def __init__(
        self,
        abstract_classifier_factory: Callable[[Dict[str, str]], AbstractClassifier],
        utilities: Utilities,
    ):
        self.abstract_classifier_factory = abstract_classifier_factory
        self.utilities = utilities

        # flag to check if classification has been run to provide a method for which to prevent retrieval
        # of unclassified attributes before classification has been ran
        self._classification_ran = False

        self.unclassified_item_count = 0
        self.unclassified_dois = []
        self.unclassified_abstracts = []
        self.unclassified_doi_abstract_dict = {}
        self.unclassified_items = []
        self.unclassified_details_dict = {"dois": [], "abstracts": [], "items": []}

    def run_classification(self, data: List[Dict]):
        """Processes and classifies a list of research metadata dictionaries.

        Args:
            data: List of dictionaries containing research metadata.

        Returns:
            List[Dict]: Modified data with classifications injected.
        """
        classified_data = self._classification_orchestrator(data)
        self._set_classification_ran_true()
        return classified_data

    def get_unclassified_item_count(self) -> int:
        """Gets the number of unclassified items.

        Returns:
            int: Number of unclassified items.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_item_count

    def get_unclassified_dois(self) -> List[str]:
        """Gets the DOIs of unclassified items.

        Returns:
            List[str]: List of unclassified DOIs.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_dois

    def get_unclassified_abstracts(self) -> List[str]:
        """Gets the abstracts of unclassified items.

        Returns:
            List[str]: List of unclassified abstracts.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_abstracts

    def get_unclassified_doi_abstract_dict(self) -> Dict[str, str]:
        """Gets the DOI to abstract mapping dictionary for unclassified items.

        Returns:
            Dict[str, str]: Dictionary mapping unclassified DOIs to abstracts.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_doi_abstract_dict

    def get_unclassified_items(self) -> List[Dict]:
        """Gets the unclassified items.

        Returns:
            List[Dict]: List of unclassified items.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_items

    def get_unclassified_details_dict(self) -> Dict:
        """Gets the details of unclassified items.

        Returns:
            Dict: Details of unclassified items.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_details_dict

    def _classification_orchestrator(self, data: List[Dict]):
        """Core classification logic for processing research metadata.

        Args:
            data: List of dictionaries containing research metadata.

        Returns:
            List[Dict]: Modified data with classifications injected.
        """
        for item in data:
            doi, abstract = self._retrieve_doi_abstract(item)
            doi_abstract_dict = self._make_doi_abstract_dict(doi, abstract)

            if not doi_abstract_dict:
                self._update_classified_instance_variables(
                    item=item, doi=doi, abstract=abstract
                )
                continue

            classifier = self.abstract_classifier_factory(
                doi_abstract_dict=doi_abstract_dict,
            )
            classifier.classify()

            self._inject_categories(
                data=item, categories=self._extract_categories(doi, classifier)
            )

        return data

    def _inject_categories(
        self,
        data: Dict,
        categories: ClassificationResultsDict | ClassificationResultsTuple,
    ) -> None:
        """Adds classification results to a research metadata dictionary.

        Args:
            data: Research metadata dictionary.
            categories: Classification results including categories and themes.
        """
        data["categories"] = {}
        data["categories"]["top"] = categories.get("top_categories", [])
        data["categories"]["mid"] = categories.get("mid_categories", [])
        data["categories"]["low"] = categories.get("low_categories", [])
        data["themes"] = categories.get("themes", [])

    def _extract_categories(
        self, doi: str, classifier: AbstractClassifier
    ) -> ClassificationResultsDict | ClassificationResultsTuple:
        """Gets classification results for a specific DOI.

        Args:
            item: Research metadata dictionary.
            doi: DOI identifier.
            classifier: Classifier instance that performed classification.

        Returns:
            ClassificationResults: Dictionary of classification results.
        """
        # .get_classification_results_by_doi() has a argument of return_type that can be set to either a dictionary or a tuple
        # By default it returns a dict, it you want a tuple you can do return_type=tuple
        return classifier.get_classification_results_by_doi(doi)

    def _make_doi_abstract_dict(self, doi: str, abstract: str) -> Dict[str, str]:
        """Creates a DOI to abstract mapping dictionary.

        Args:
            doi: DOI identifier.
            abstract: Research abstract text.

        Returns:
            Dict[str, str]: Dictionary mapping DOI to abstract.
        """
        if doi and abstract:
            return {doi: abstract}
        return {}

    def _retrieve_doi_abstract(self, item: Dict) -> Tuple[str, str]:
        """Extracts DOI and abstract from a research metadata dictionary.

        Args:
            item: Research metadata dictionary.

        Returns:
            Tuple[str, str]: DOI and abstract pair.
        """
        result = self.utilities.get_attributes(
            item, [AttributeTypes.CROSSREF_DOI, AttributeTypes.CROSSREF_ABSTRACT]
        )
        doi = (
            result[AttributeTypes.CROSSREF_DOI][1]
            if result[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        abstract = (
            result[AttributeTypes.CROSSREF_ABSTRACT][1]
            if result[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        return doi, abstract

    def _update_classified_instance_variables(
        self, item: Dict, doi: str, abstract: str
    ) -> None:
        """Updates tracking variables for unclassified items.

        Args:
            item: Research metadata dictionary.
            doi: DOI identifier.
            abstract: Research abstract text.
        """
        self.unclassified_item_count += 1
        (
            self.unclassified_dois.append(doi)
            if doi
            else self.unclassified_dois.append("NULL")
        )
        (
            self.unclassified_abstracts.append(abstract)
            if abstract
            else self.unclassified_abstracts.append("NULL")
        )
        self.unclassified_doi_abstract_dict[doi] = abstract
        self.unclassified_items.append(item)
        (
            self.unclassified_details_dict["dois"].append(doi)
            if doi
            else self.unclassified_details_dict["dois"].append("NULL")
        )
        (
            self.unclassified_details_dict["abstracts"].append(abstract)
            if abstract
            else self.unclassified_details_dict["abstracts"].append("NULL")
        )
        self.unclassified_details_dict["items"].append(item)

    def _set_classification_ran_true(self) -> None:
        """Sets the classification ran flag to true."""
        self._classification_ran = True

    def _has_ran_classification(self) -> bool:
        """Checks if classification has been run."""
        return self._classification_ran

    def _validate_classification_ran(self, classification_ran: bool) -> None:
        """Validates if classification has been run.

        Args:
            classification_ran: Boolean indicating if classification has been run.

        Raises:
            RuntimeError: If classification has not been run yet.
        """
        if not classification_ran:
            raise RuntimeError(
                "Classification has not been run yet. "
                "Call run_classification() on your data before attempting to retrieve unclassified attributes. "
                "Data should be a list of loaded crossref JSON objects."
            )