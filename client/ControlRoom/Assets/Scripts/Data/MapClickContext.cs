// MapClickContext.cs — 맵 클릭 1회의 컨텍스트(순수 POCO). 액션 실행에 필요한 정보 묶음.
// worldX/Y: map 프레임 좌표(m), screenX/Y: 패널 좌표(메뉴 위치), selectedRobotId: 명령 대상.
namespace URHYNIX.ControlRoom.Data
{
    public class MapClickContext
    {
        public float worldX;
        public float worldY;
        public float screenX;
        public float screenY;
        public string selectedRobotId;
    }
}
