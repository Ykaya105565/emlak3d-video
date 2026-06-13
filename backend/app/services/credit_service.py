from sqlalchemy.ext.asyncio import AsyncSession
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.models.video_job import VideoResolution
from app.models.listing import InteriorSourceType


def calculate_credit_cost(
    duration: int,
    resolution: VideoResolution,
    interior_source: InteriorSourceType,
    is_watermarked: bool,
) -> float:
    """
    Kredi = süre × çözünürlük × iç mekân tipi × özellik
    Spec §9'a göre iskelet:
      Süre: 15sn baz=1, her +15sn +1
      Çözünürlük: 1080p=0, 4K=+1
      İç mekân: listing_data=+0, photos=+1, gml_3d=+2
      Watermark: 0 (ücretsiz deneme)
    """
    if is_watermarked:
        return 0.0

    duration_credits = max(1, duration // 15)
    resolution_credits = 1 if resolution == VideoResolution.UHD_4K else 0
    interior_credits = {
        InteriorSourceType.LISTING_DATA: 0,
        InteriorSourceType.PHOTOS: 1,
        InteriorSourceType.GML_3D: 2,
    }.get(interior_source, 0)

    return float(duration_credits + resolution_credits + interior_credits)


async def deduct_credits(
    db: AsyncSession,
    wallet: CreditWallet,
    amount: float,
    listing_id: str,
) -> None:
    wallet.balance -= amount
    tx = CreditTransaction(
        wallet_id=wallet.id,
        transaction_type=TransactionType.CONSUME,
        amount=-amount,
        description=f"Video render: ilan {listing_id}",
        video_job_id=listing_id,
    )
    db.add(tx)
