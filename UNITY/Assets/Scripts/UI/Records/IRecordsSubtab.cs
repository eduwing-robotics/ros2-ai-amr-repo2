// IRecordsSubtab.cs — 기록 탭 서브탭 공통 인터페이스.
// RecordsPageView가 서브탭 전환 시 Build/Load/Refresh를 통일해서 호출한다.
namespace URHYNIX.ControlRoom.UI.Records
{
    public interface IRecordsSubtab
    {
        void Build();
        void Load();
        void Refresh();
    }
}
