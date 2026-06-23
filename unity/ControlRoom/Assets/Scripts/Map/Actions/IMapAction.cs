// IMapAction.cs — 맵 우클릭 컨텍스트 메뉴 액션 인터페이스(확장점).
// 새 액션은 이 인터페이스만 구현해 MapActionRegistry에 등록하면 메뉴에 자동 노출.
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public interface IMapAction
    {
        string Id { get; }
        string DisplayName { get; }
        bool AppliesTo(MapClickContext ctx);
        void Execute(MapClickContext ctx);
    }
}
