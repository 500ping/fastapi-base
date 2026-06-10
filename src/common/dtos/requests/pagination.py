from pydantic import BaseModel, Field

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationParams(BaseModel):
    """Reusable pagination query params.

    Use it directly, or subclass to add endpoint-specific (optional) filters::

        class ListWidgetsParams(PaginationParams):
            status: Optional[WidgetStatus] = None

    Then accept it as query params in a route::

        async def list_widgets(params: Annotated[ListWidgetsParams, Query()]):
            ...
    """

    page: int = Field(default=1, ge=1, description="1-based page number")
    size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Items per page",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size
