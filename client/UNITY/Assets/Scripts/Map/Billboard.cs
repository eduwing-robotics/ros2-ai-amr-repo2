// Billboard.cs — 매 프레임 지정된 카메라를 향해 회전(웨이포인트 번호 라벨 등 3D 텍스트가 항상 읽히게).
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public class Billboard : MonoBehaviour
    {
        public Camera target;

        void LateUpdate()
        {
            if (target == null) return;
            transform.rotation = target.transform.rotation;
        }
    }
}
